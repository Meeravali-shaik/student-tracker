import streamlit as st
import pandas as pd
import plotly.express as px
from utils.helpers import get_student_progress, get_current_problem, streak_stats, compute_score
from utils.auth import require_student

def main(auth):
    """Render the student dashboard with metrics and charts."""
    require_student(auth)
    st.title("🚀 Student Dashboard")

    # Load progress data
    progress_df = get_student_progress(auth.user_id)
    current = get_current_problem(auth.user_id)
    streak = streak_stats(auth.user_id)
    score = compute_score(auth.user_id)

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Solved", f"{progress_df['solved'].sum()}")
    col2.metric("Current Problem", current.get('title', 'N/A'))
    col3.metric("Completion %", f"{progress_df['solved'].sum() / len(progress_df) * 100:.1f}%")
    col4.metric("Streak (days)", f"{streak['days']}")

    # Plotly timeline of solved problems
    solved = progress_df[progress_df['status'] == 'completed']
    if not solved.empty:
        fig = px.line(
            solved,
            x='completed_at',
            y='order_no',
            title='Problems Solved Over Time',
            markers=True,
        )
        st.plotly_chart(fig, use_container_width=True)

    # Badge display (simple icons)
    badge_map = {
        "bronze": score >= 10,
        "silver": score >= 25,
        "gold": score >= 50,
        "club100": score >= 100,
        "streak7": streak['days'] >= 7,
        "streak30": streak['days'] >= 30,
    }
    badge_cols = st.columns(len(badge_map))
    for i, (badge, earned) in enumerate(badge_map.items()):
        with badge_cols[i]:
            img_path = f"assets/badges/{badge}.svg"
            if earned:
                st.image(img_path, width=80, caption=badge.title())
            else:
                st.image(img_path, width=80, opacity=0.3, caption=badge.title())
