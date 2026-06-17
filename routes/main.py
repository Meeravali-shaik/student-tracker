from flask import Blueprint, render_template, session, redirect, url_for, request, flash
from database.supabase_client import supabase
from utils.helpers import get_student_progress, streak_stats, compute_score

main_bp = Blueprint("main", __name__)

@main_bp.before_request
def require_login():
    if "user_id" not in session:
        flash("Please log in to access this page.", "warning")
        return redirect(url_for("auth.login"))

@main_bp.route("/dashboard")
def dashboard():
    user_id = session.get("user_id")
    name = session.get("name")
    
    # Get progress using existing helper
    progress_df = get_student_progress(user_id)
    total_problems = len(progress_df)
    solved_count = len(progress_df[progress_df["solved"] == True])
    progress_percentage = (solved_count / total_problems * 100) if total_problems > 0 else 0
    
    score = compute_score(user_id)
    streak = streak_stats(user_id).get("days", 0)
    
    # Recent activity
    recent = progress_df[progress_df["solved"] == True].sort_values("completed_at", ascending=False).head(5)
    recent_list = recent.to_dict(orient="records")
    
    return render_template("dashboard.html", 
                           name=name, 
                           solved_count=solved_count, 
                           total_problems=total_problems,
                           progress_percentage=round(progress_percentage),
                           score=score,
                           streak=streak,
                           recent_activity=recent_list)

@main_bp.route("/tracks")
def tracks():
    user_id = session.get("user_id")
    progress_df = get_student_progress(user_id)
    
    # Group problems by track
    tracks_data = {}
    if not progress_df.empty:
        for track_name, group in progress_df.groupby("track"):
            tracks_data[track_name] = group.sort_values("order_no").to_dict(orient="records")
            
    return render_template("tracks.html", tracks=tracks_data)

@main_bp.route("/leaderboard")
def leaderboard():
    # Fetch all students and compute their scores
    students = supabase.from_("students").select("id, name, roll_no").execute().data
    
    leaderboard_data = []
    for s in students:
        try:
            score = compute_score(s["id"])
        except Exception:
            # Retry once; if still failing, default to 0
            try:
                score = compute_score(s["id"])
            except Exception:
                score = 0
        try:
            streak = streak_stats(s["id"]).get("days", 0)
        except Exception:
            streak = 0
        leaderboard_data.append({
            "name": s["name"],
            "roll_no": s["roll_no"],
            "score": score,
            "streak": streak
        })
        
    # Sort by score descending
    leaderboard_data = sorted(leaderboard_data, key=lambda x: x["score"], reverse=True)
    
    return render_template("leaderboard.html", leaderboard=leaderboard_data)

@main_bp.route("/profile", methods=["GET", "POST"])
def profile():
    user_id = session.get("user_id")
    
    if request.method == "POST":
        name = request.form.get("name")
        roll_no = request.form.get("roll_no")
        leetcode = request.form.get("leetcode_username")
        hackerrank = request.form.get("hackerrank_username")
        
        data = {
            "name": name,
            "roll_no": roll_no,
            "leetcode_username": leetcode,
            "hackerrank_username": hackerrank
        }
        
        supabase.from_("students").update(data).eq("id", user_id).execute()
        session["name"] = name  # Update session name
        flash("Profile updated successfully!", "success")
        return redirect(url_for("main.profile"))
        
    # GET request
    user = supabase.from_("students").select("*").eq("id", user_id).execute().data[0]
    return render_template("profile.html", user=user)

# ----------------------------------------------------------------------
# Solve problem endpoint – records completion and unlocks next problem
# ----------------------------------------------------------------------
from datetime import datetime

@main_bp.route("/solve/<uuid:problem_id>", methods=["POST"])
def solve_problem(problem_id):
    # Ensure the user is logged in
    if "user_id" not in session:
        flash("Please log in to solve a problem.", "warning")
        return redirect(url_for("auth.login"))

    user_id = session.get("user_id")
    # Upsert a progress row marking the problem as completed
    from uuid import UUID
    # Ensure problem_id is a string for Supabase
    problem_id_str = str(problem_id) if isinstance(problem_id, UUID) else str(problem_id)
    supabase.from_("progress") \
        .upsert({
            "student_id": user_id,
            "problem_id": problem_id_str,
            "status": "completed",
            "completed_at": datetime.utcnow().isoformat()
        }, on_conflict="student_id,problem_id") \
        .execute()

    flash("Problem marked as completed!", "success")
    # Redirect back to the tracks view where unlocking will be recomputed
    return redirect(url_for("main.tracks"))
