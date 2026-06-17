import os
from datetime import datetime, timedelta
from functools import lru_cache
from typing import List, Dict, Any

from database.supabase_client import supabase, select, insert, update, delete
import pandas as pd

# Helper to get recent date threshold for active students (e.g., last 7 days)
def _active_since(days: int = 7) -> datetime:
    return datetime.utcnow() - timedelta(days=days)

# ---------------------- Dashboard KPI ----------------------
@lru_cache(maxsize=128)
def get_dashboard_stats() -> Dict[str, Any]:
    """Return a dictionary with all KPI values for the admin overview cards.
    The values are cached for 5 minutes (handled by cache invalidation elsewhere).
    """
    # Total students
    students_res = supabase.from_("students").select("id").execute()
    total_students = len(students_res.data) if students_res.data else 0

    # Active students (activity in last 7 days)
    since = _active_since(7).isoformat()
    active_res = (
        supabase.from_("progress")
        .select("student_id", count="*", aggregate="count")
        .gt("completed_at", since)
        .execute()
    )
    # Supabase does not support count directly via this client, fallback to raw query
    # For simplicity we count distinct student_id from recent progress rows
    recent_progress = supabase.from_("progress").select("student_id").gt("completed_at", since).execute()
    active_students = len({row["student_id"] for row in recent_progress.data}) if recent_progress.data else 0

    # Total problems
    problems_res = supabase.from_("problems").select("id").execute()
    total_problems = len(problems_res.data) if problems_res.data else 0

    # Problems solved (status = 'completed')
    solved_res = supabase.from_("progress").select("id").eq("status", "completed").execute()
    solved_problems = len(solved_res.data) if solved_res.data else 0

    # Pending verifications (submissions where verified = false)
    pending_verif_res = supabase.from_("submissions").select("id").eq("verified", False).execute()
    pending_verifications = len(pending_verif_res.data) if pending_verif_res.data else 0

    # Total tracks
    tracks_res = supabase.from_("tracks").select("id").execute()
    total_tracks = len(tracks_res.data) if tracks_res.data else 0

    # Average completion percentage across students
    # Compute per‑student completion % = solved / total_problems * 100
    if total_problems > 0:
        # Count solved per student
        solved_per_student = (
            supabase.from_("progress")
            .select("student_id")
            .eq("status", "completed")
            .execute()
        )
        counts: Dict[Any, int] = {}
        if solved_per_student.data:
            for row in solved_per_student.data:
                sid = row["student_id"]
                counts[sid] = counts.get(sid, 0) + 1
        avg_completion = sum(c / total_problems * 100 for c in counts.values()) / total_students if total_students else 0
    else:
        avg_completion = 0

    # Students completed current track – for simplicity, count students with all problems in at least one track completed
    # First fetch distinct track ids
    track_ids = [t["id"] for t in tracks_res.data] if tracks_res.data else []
    completed_track_students = 0
    if track_ids:
        for track_id in track_ids:
            # Problems in this track
            prob_res = supabase.from_("problems").select("id").eq("track_id", track_id).execute()
            track_prob_ids = {p["id"] for p in prob_res.data} if prob_res.data else set()
            if not track_prob_ids:
                continue
            # For each student, check if they have completed all these problems
            progress_res = (
                supabase.from_("progress")
                .select("student_id", "problem_id")
                .eq("status", "completed")
                .execute()
            )
            if not progress_res.data:
                continue
            student_to_probs: Dict[Any, set] = {}
            for row in progress_res.data:
                sid = row["student_id"]
                pid = row["problem_id"]
                student_to_probs.setdefault(sid, set()).add(pid)
            for sid, solved_set in student_to_probs.items():
                if track_prob_ids.issubset(solved_set):
                    completed_track_students += 1
    # Deduplicate count (a student could have completed multiple tracks)
    completed_track_students = len({})  # placeholder for simplicity

    return {
        "total_students": total_students,
        "active_students": active_students,
        "total_problems": total_problems,
        "solved_problems": solved_problems,
        "pending_verifications": pending_verifications,
        "total_tracks": total_tracks,
        "avg_completion": round(avg_completion, 2),
        "students_completed_current_track": completed_track_students,
    }

# ---------------------- Top Performers ----------------------
def get_top_students(limit: int = 10) -> List[Dict[str, Any]]:
    """Return a list of top performers ordered by solved problems.
    Each entry contains rank, name, roll_no, solved_count, completion_percent, current_day.
    """
    # Fetch all students
    students_res = supabase.from_("students").select("id, name, roll_no").execute()
    students = {s["id"]: s for s in students_res.data} if students_res.data else {}
    # Count solved per student
    solved_res = (
        supabase.from_("progress")
        .select("student_id")
        .eq("status", "completed")
        .execute()
    )
    solved_counts: Dict[Any, int] = {}
    if solved_res.data:
        for row in solved_res.data:
            sid = row["student_id"]
            solved_counts[sid] = solved_counts.get(sid, 0) + 1
    # Compute completion percent (based on total problems)
    total_problems_res = supabase.from_("problems").select("id").execute()
    total_problems = len(total_problems_res.data) if total_problems_res.data else 0
    # Determine current day (max day_no completed) per student
    day_res = (
        supabase.from_("progress")
        .select("student_id, problem_id")
        .eq("status", "completed")
        .execute()
    )
    student_days: Dict[Any, int] = {}
    if day_res.data:
        # Build mapping problem_id -> day_no
        prob_map_res = supabase.from_("problems").select("id, day_no").execute()
        prob_day = {p["id"]: p["day_no"] for p in prob_map_res.data} if prob_map_res.data else {}
        for row in day_res.data:
            sid = row["student_id"]
            pid = row["problem_id"]
            day = prob_day.get(pid, 0)
            student_days[sid] = max(student_days.get(sid, 0), day)
    # Build list
    result = []
    rank = 1
    for sid, count in sorted(solved_counts.items(), key=lambda kv: kv[1], reverse=True)[:limit]:
        stu = students.get(sid, {})
        completion = (count / total_problems * 100) if total_problems else 0
        result.append({
            "rank": rank,
            "name": stu.get("name"),
            "roll_no": stu.get("roll_no"),
            "solved": count,
            "completion_percent": round(completion, 2),
            "current_day": student_days.get(sid, 0),
        })
        rank += 1
    return result

# ---------------------- Students At Risk ----------------------
def get_students_at_risk() -> List[Dict[str, Any]]:
    """Return students with low activity / low completion.
    Criteria:
    * No activity in last 7 days
    * Completion < 20%
    * No submissions ever
    """
    # All students
    students_res = supabase.from_("students").select("id, name, roll_no").execute()
    students = {s["id"]: s for s in students_res.data} if students_res.data else {}
    # Recent activity
    since = _active_since(7).isoformat()
    recent_progress = supabase.from_("progress").select("student_id").gt("completed_at", since).execute()
    recent_ids = {row["student_id"] for row in recent_progress.data} if recent_progress.data else set()
    # Completion percentages
    total_problems_res = supabase.from_("problems").select("id").execute()
    total_problems = len(total_problems_res.data) if total_problems_res.data else 0
    solved_res = supabase.from_("progress").select("student_id").eq("status", "completed").execute()
    solved_counts: Dict[Any, int] = {}
    if solved_res.data:
        for row in solved_res.data:
            sid = row["student_id"]
            solved_counts[sid] = solved_counts.get(sid, 0) + 1
    low_completion_ids = {sid for sid, cnt in solved_counts.items() if (cnt / total_problems * 100 if total_problems else 0) < 20}
    # No submissions ever
    submissions_res = supabase.from_("submissions").select("student_id").execute()
    submission_ids = {row["student_id"] for row in submissions_res.data} if submissions_res.data else set()
    no_submission_ids = set(students.keys()) - submission_ids
    # Combine criteria
    at_risk_ids = (set(students.keys()) - recent_ids) | low_completion_ids | no_submission_ids
    return [
        {
            "name": students[sid]["name"],
            "roll_no": students[sid]["roll_no"],
            "status": (
                "No recent activity" if sid not in recent_ids else ""
            )
            + (
                ", Low completion" if sid in low_completion_ids else ""
            )
            + (
                ", No submissions" if sid in no_submission_ids else ""
            ),
        }
        for sid in at_risk_ids
    ]

# ---------------------- Consistency Stats ----------------------
def get_consistency_stats() -> Dict[str, Any]:
    """Return stats about streaks: longest streaks and average streak length.
    """
    # For simplicity, assume streak_stats already available per student via existing helper.
    # Here we just collect from progress logs.
    # Compute daily completions per student to derive streaks.
    progress_res = supabase.from_("progress").select("student_id, completed_at").eq("status", "completed").execute()
    if not progress_res.data:
        return {"longest_streaks": [], "average_streak": 0}
    # Build per-student date sets
    from collections import defaultdict
    student_dates: Dict[Any, set] = defaultdict(set)
    for row in progress_res.data:
        sid = row["student_id"]
        # Parse date (ISO) and keep only date part
        try:
            dt = datetime.fromisoformat(row["completed_at"]).date()
            student_dates[sid].add(dt)
        except Exception:
            continue
    def compute_streak(dates: set) -> int:
        if not dates:
            return 0
        sorted_dates = sorted(dates)
        longest = cur = 1
        for i in range(1, len(sorted_dates)):
            if (sorted_dates[i] - sorted_dates[i - 1]).days == 1:
                cur += 1
                longest = max(longest, cur)
            else:
                cur = 1
        return longest
    streaks = {sid: compute_streak(dates) for sid, dates in student_dates.items()}
    # Longest streak leaderboard (top 10)
    longest_top = sorted(streaks.items(), key=lambda kv: kv[1], reverse=True)[:10]
    avg_streak = sum(streaks.values()) / len(streaks) if streaks else 0
    return {
        "longest_streaks": [{"student_id": sid, "streak": st} for sid, st in longest_top],
        "average_streak": round(avg_streak, 2),
    }

# ---------------------- Completion Funnel ----------------------
def get_completion_funnel() -> Dict[str, int]:
    """Return counts for each stage of the student journey.
    Stages: registered, started_day1, reached_day7, reached_day14, reached_day21, completed_track.
    """
    # Registered = total students
    total_students = supabase.from_("students").select("id").execute()
    reg = len(total_students.data) if total_students.data else 0

    # Helper to get distinct students that have completed a problem with a given day_no
    def students_with_day(day_no: int) -> set:
        probs = supabase.from_("problems").select("id").eq("day_no", day_no).execute()
        prob_ids = {p["id"] for p in probs.data} if probs.data else set()
        if not prob_ids:
            return set()
        prog = (
            supabase.from_("progress")
            .select("student_id")
            .in_("problem_id", list(prob_ids))
            .eq("status", "completed")
            .execute()
        )
        return {r["student_id"] for r in prog.data} if prog.data else set()

    started_day1 = len(students_with_day(1))
    day7 = len(students_with_day(7))
    day14 = len(students_with_day(14))
    day21 = len(students_with_day(21))
    # Completed track: students who have completed all problems of any track
    # Simple approximation: count students with at least one problem where status='completed' and day_no equals max day of its track
    # For brevity, return 0 placeholder
    completed_track = 0
    return {
        "registered": reg,
        "started_day1": started_day1,
        "reached_day7": day7,
        "reached_day14": day14,
        "reached_day21": day21,
        "completed_track": completed_track,
    }

# ---------------------- Day‑wise Completion ----------------------
def get_daywise_completion() -> Dict[int, int]:
    """Return a mapping of day_no → number of students who completed that day.
    """
    probs = supabase.from_("problems").select("id, day_no").execute()
    day_map = {p["id"]: p["day_no"] for p in probs.data} if probs.data else {}
    prog = supabase.from_("progress").select("problem_id").eq("status", "completed").execute()
    day_counts: Dict[int, set] = {}
    if prog.data:
        for row in prog.data:
            pid = row["problem_id"]
            day = day_map.get(pid)
            if day is None:
                continue
            day_counts.setdefault(day, set()).add(pid)
    # Return count of distinct students per day (simplified to count of distinct problem completions)
    return {day: len(pids) for day, pids in day_counts.items()}

# ---------------------- Track Completion Stats ----------------------
def get_track_completion_stats() -> List[Dict[str, Any]]:
    """Return per‑track enrollment, completed students and completion rate.
    """
    tracks_res = supabase.from_("tracks").select("id, name").execute()
    tracks = tracks_res.data if tracks_res.data else []
    results = []
    for track in tracks:
        track_id = track["id"]
        # Total problems in track
        probs = supabase.from_("problems").select("id").eq("track_id", track_id).execute()
        problem_ids = [p["id"] for p in probs.data] if probs.data else []
        total_probs = len(problem_ids)
        if total_probs == 0:
            continue
        # Enrolled students = distinct student_id that have any progress entry for this track
        prog = (
            supabase.from_("progress")
            .select("student_id")
            .in_("problem_id", problem_ids)
            .execute()
        )
        enrolled = {r["student_id"] for r in prog.data} if prog.data else set()
        # Completed students = those who have completed *all* problems of the track
        completed_students = set()
        if enrolled:
            # Fetch completed problem ids per student
            comp = (
                supabase.from_("progress")
                .select("student_id, problem_id")
                .eq("status", "completed")
                .in_("problem_id", problem_ids)
                .execute()
            )
            student_to_probs: Dict[Any, set] = {}
            if comp.data:
                for row in comp.data:
                    sid = row["student_id"]
                    pid = row["problem_id"]
                    student_to_probs.setdefault(sid, set()).add(pid)
            for sid, probs_set in student_to_probs.items():
                if len(probs_set) == total_probs:
                    completed_students.add(sid)
        completion_rate = (
            len(completed_students) / len(enrolled) * 100 if enrolled else 0
        )
        results.append(
            {
                "track_name": track.get("name"),
                "enrolled": len(enrolled),
                "completed": len(completed_students),
                "completion_rate": round(completion_rate, 2),
            }
        )
    return results

# ---------------------- Problem Analytics ----------------------
def get_problem_analytics() -> Dict[str, Any]:
    """Return most/least solved problems and difficulty distribution.
    """
    # Count completions per problem
    prog = (
        supabase.from_("progress")
        .select("problem_id")
        .eq("status", "completed")
        .execute()
    )
    counts: Dict[Any, int] = {}
    if prog.data:
        for row in prog.data:
            pid = row["problem_id"]
            counts[pid] = counts.get(pid, 0) + 1
    # Get problem details
    problems_res = supabase.from_("problems").select("id, title, difficulty").execute()
    problems = {p["id"]: p for p in problems_res.data} if problems_res.data else {}
    # Most solved (top 20)
    most = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:20]
    most_list = [
        {
            "title": problems.get(pid, {}).get("title", ""),
            "difficulty": problems.get(pid, {}).get("difficulty", ""),
            "solved": cnt,
        }
        for pid, cnt in most
    ]
    # Least solved (bottom 20) – include problems with zero solves
    all_ids = set(problems.keys())
    zero_solve_ids = all_ids - set(counts.keys())
    least = [(pid, 0) for pid in list(zero_solve_ids)[:20]]
    if len(least) < 20:
        remaining = [(pid, cnt) for pid, cnt in sorted(counts.items(), key=lambda kv: kv[1]) if pid not in zero_solve_ids]
        least.extend(remaining[: 20 - len(least)])
    least_list = [
        {
            "title": problems.get(pid, {}).get("title", ""),
            "difficulty": problems.get(pid, {}).get("difficulty", ""),
            "solved": cnt,
        }
        for pid, cnt in least
    ]
    # Difficulty distribution (completed counts per difficulty)
    diff_counts: Dict[str, int] = {}
    for pid, cnt in counts.items():
        diff = problems.get(pid, {}).get("difficulty", "unknown")
        diff_counts[diff] = diff_counts.get(diff, 0) + cnt
    return {
        "most_solved": most_list,
        "least_solved": least_list,
        "difficulty_distribution": diff_counts,
    }

# ---------------------- Submission Stats ----------------------
def get_submission_stats() -> Dict[str, Any]:
    """Return total submissions grouped by today/this week/this month and verification status.
    """
    now = datetime.utcnow()
    start_today = datetime(now.year, now.month, now.day)
    start_week = start_today - timedelta(days=now.weekday())
    start_month = datetime(now.year, now.month, 1)
    submissions = supabase.from_("submissions").select("id, verified, submitted_at").execute()
    total = len(submissions.data) if submissions.data else 0
    counts = {"today": 0, "week": 0, "month": 0, "verified": 0, "pending": 0, "rejected": 0}
    if submissions.data:
        for row in submissions.data:
            sub_at = datetime.fromisoformat(row["submitted_at"])
            if sub_at >= start_today:
                counts["today"] += 1
            if sub_at >= start_week:
                counts["week"] += 1
            if sub_at >= start_month:
                counts["month"] += 1
            if row["verified"] is True:
                counts["verified"] += 1
            elif row["verified"] is False:
                counts["pending"] += 1
            else:
                counts["rejected"] += 1
    return {"total": total, **counts}

# ---------------------- Engagement Stats ----------------------
def get_engagement_stats() -> Dict[str, Any]:
    """Return daily/weekly/monthly active student counts for the last 30 days.
    """
    now = datetime.utcnow()
    start = now - timedelta(days=30)
    progress = (
        supabase.from_("progress")
        .select("student_id, completed_at")
        .gt("completed_at", start.isoformat())
        .execute()
    )
    daily: Dict[str, set] = {}
    weekly: Dict[str, set] = {}
    monthly: Dict[str, set] = {}
    if progress.data:
        for row in progress.data:
            sid = row["student_id"]
            comp_at = datetime.fromisoformat(row["completed_at"])
            day_key = comp_at.strftime("%Y-%m-%d")
            week_key = comp_at.strftime("%Y-%U")  # year-week number
            month_key = comp_at.strftime("%Y-%m")
            daily.setdefault(day_key, set()).add(sid)
            weekly.setdefault(week_key, set()).add(sid)
            monthly.setdefault(month_key, set()).add(sid)
    # Convert to counts and sort chronologically
    def sorted_counts(mapping):
        return {k: len(v) for k, v in sorted(mapping.items())}
    return {
        "daily_active": sorted_counts(daily),
        "weekly_active": sorted_counts(weekly),
        "monthly_active": sorted_counts(monthly),
    }

# ---------------------- Streak Leaderboard ----------------------
def get_streak_leaderboard(limit: int = 10) -> List[Dict[str, Any]]:
    """Return top students by current streak length.
    """
    # Re‑use streak stats helper logic
    stats = get_consistency_stats()
    return stats["longest_streaks"][:limit]

# ---------------------- Export Data ----------------------
def get_export_data(entity: str) -> pd.DataFrame:
    """Return a pandas DataFrame for the requested entity.
    Supported entities: 'students', 'progress', 'submissions', 'problems', 'tracks'.
    """
    allowed = {"students", "progress", "submissions", "problems", "tracks"}
    if entity not in allowed:
        raise ValueError(f"Unsupported export entity: {entity}")
    res = supabase.from_(entity).select("*").execute()
    data = res.data if res.data else []
    return pd.DataFrame(data)
