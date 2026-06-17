# utils/helpers.py
"""Utility functions used across the Streamlit app.

Provides:
- CSS loader
- Student progress retrieval
- Current problem lookup
- Streak calculation
- Score computation
- Profile update helper
"""

import streamlit as st
from postgrest.exceptions import APIError
import pandas as pd
from datetime import datetime, timedelta
from database.supabase_client import supabase

# ----------------------------------------------------------------------
# Styling
# ----------------------------------------------------------------------
def load_css(path: str = "assets/style.css"):
    """Read a CSS file and inject it into the Streamlit app.
    ``path`` should be relative to the project root.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            css = f.read()
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning(f"CSS file not found: {path}")

# ----------------------------------------------------------------------
# Progress helpers
# ----------------------------------------------------------------------
def get_student_progress(student_id: int) -> pd.DataFrame:
    """Return a DataFrame with all problems and the student's status.
    Columns: id, title, order_no, difficulty, track (optional), status, completed_at, solved (bool)"""
    # All problems ordered globally
    # First try to fetch problems with a 'track' column (legacy schema)
    try:
        problems = (
            supabase.from_("problems")
            .select("id, title, order_no, difficulty, track, problem_url")
            .order("order_no")
            .execute()
            .data
        )
    except APIError as e:
        # If the 'track' column does not exist, fallback to a separate tracks table
        if "track" in str(e):
            # Fetch problems with track_id
            problems = (
                supabase.from_("problems")
                .select("id, title, order_no, difficulty, track_id, problem_url")
                .order("order_no")
                .execute()
                .data
            )
            # Fetch track names and map them to problems
            track_rows = (
                supabase.from_("tracks")
                .select("id, name")
                .execute()
                .data
            )
            track_map = {row["id"]: row["name"] for row in track_rows}
            for prob in problems:
                prob["track"] = track_map.get(prob.get("track_id"), "General")
                prob.pop("track_id", None)
        else:
            raise
    prob_df = pd.DataFrame(problems)
    # Ensure 'link' column exists (rename from problem_url if needed)
    if "problem_url" in prob_df.columns:
        prob_df = prob_df.rename(columns={"problem_url": "link"})
    elif "link" not in prob_df.columns:
        prob_df["link"] = None
        
    if "track" not in prob_df.columns:
        prob_df["track"] = "General"
    # Reorder columns for consistency
    prob_df = prob_df[["id", "title", "order_no", "difficulty", "track", "link"]]

    # Student progress rows
    progress = (
        supabase.from_("progress")
        .select("problem_id, status, completed_at")
        .eq("student_id", student_id)
        .execute()
        .data
    )
    prog_df = pd.DataFrame(progress, columns=["problem_id", "status", "completed_at"])

    merged = prob_df.merge(prog_df, left_on="id", right_on="problem_id", how="left")
    merged = prob_df.merge(prog_df, left_on="id", right_on="problem_id", how="left")
    merged["completed_at"] = pd.to_datetime(merged["completed_at"], errors="coerce")
    
    # Calculate unlocking per track
    # Sort to ensure order_no is respected
    merged = merged.sort_values(by=["track", "order_no"])
    
    # We will iterate and set the correct status
    final_rows = []
    for track_name, group in merged.groupby("track", sort=False):
        track_unlocked = False
        for _, row in group.iterrows():
            if pd.isna(row["status"]):
                # No progress record
                if not track_unlocked:
                    row["status"] = "unlocked"
                    track_unlocked = True
                else:
                    row["status"] = "locked"
            elif row["status"] != "completed":
                # E.g. explicitly marked as unlocked or locked
                if not track_unlocked:
                    row["status"] = "unlocked"
                    track_unlocked = True
                else:
                    row["status"] = "locked"
            # If it's completed, we keep it as completed and haven't unlocked the next one yet
            final_rows.append(row.to_dict())
            
    if not final_rows:
        # Return an empty dataframe with correct columns if there are no problems
        return pd.DataFrame(columns=["id", "title", "order_no", "difficulty", "track", "problem_id", "status", "completed_at", "solved"])
        
    result_df = pd.DataFrame(final_rows)
    result_df["solved"] = result_df["status"] == "completed"
        
    return result_df


def get_current_problem(student_id: int):
    """Return the first problem that is unlocked (status == 'unlocked').
    If none are unlocked, returns an empty dict.
    """
    progress = get_student_progress(student_id)
    unlocked = progress[progress["status"] == "unlocked"].sort_values("order_no")
    if not unlocked.empty:
        return unlocked.iloc[0].to_dict()
    return {}

# ----------------------------------------------------------------------
# Streak calculation
# ----------------------------------------------------------------------
def streak_stats(student_id: int) -> dict:
    """Calculate the number of consecutive days the student solved at least one problem.
    Returns a dict ``{"days": int}``.
    """
    # Fetch completion dates
    completions = (
        supabase.from_("progress")
        .select("completed_at")
        .eq("student_id", student_id)
        .eq("status", "completed")
        .execute()
        .data
    )
    dates = [datetime.fromisoformat(c["completed_at"]).date() for c in completions if c["completed_at"]]
    if not dates:
        return {"days": 0}
    dates = sorted(set(dates), reverse=True)
    streak = 0
    today = datetime.utcnow().date()
    for d in dates:
        if (today - d).days == streak:
            streak += 1
        else:
            break
    return {"days": streak}

# ----------------------------------------------------------------------
# Scoring & badge helpers
# ----------------------------------------------------------------------
def compute_score(student_id: int) -> int:
    """Simple score: 10 points per solved problem + 5 points per streak day."""
    solved_count = (
        supabase.from_("progress")
        .select("id", count="exact")
        .eq("student_id", student_id)
        .eq("status", "completed")
        .execute()
        .count
    )
    streak = streak_stats(student_id)["days"]
    return solved_count * 10 + streak * 5

# ----------------------------------------------------------------------
# Profile update helper
# ----------------------------------------------------------------------
def update_profile(student_id: int, name: str, roll_no: str, leetcode_username: str, hackerrank_username: str):
    """Update mutable fields of a student record."""
    data = {
        "name": name,
        "roll_no": roll_no,
        "leetcode_username": leetcode_username,
        "hackerrank_username": hackerrank_username,
    }
    supabase.from_("students").update(data).eq("id", student_id).execute()
