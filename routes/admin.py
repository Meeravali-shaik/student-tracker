from flask import Blueprint, render_template, session, redirect, url_for, flash, jsonify, Response, request
from utils.decorators import admin_required
from services.analytics_service import (
    get_dashboard_stats,
    get_top_students,
    get_students_at_risk,
    get_consistency_stats,
    get_completion_funnel,
    get_daywise_completion,
    get_track_completion_stats,
    get_problem_analytics,
    get_submission_stats,
    get_engagement_stats,
    get_streak_leaderboard,
    get_export_data,
)

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/')
@admin_required
def admin_index():
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    # Render dashboard; detailed data will be fetched via AJAX API calls
    return render_template('admin/dashboard.html')

# ---------- API endpoints for AJAX ----------
@admin_bp.route('/api/dashboard_stats')
@admin_required
def api_dashboard_stats():
    return jsonify(get_dashboard_stats())

@admin_bp.route('/api/top_students')
@admin_required
def api_top_students():
    return jsonify(get_top_students())

@admin_bp.route('/api/students_at_risk')
@admin_required
def api_students_at_risk():
    return jsonify(get_students_at_risk())

@admin_bp.route('/api/consistency')
@admin_required
def api_consistency():
    return jsonify(get_consistency_stats())

@admin_bp.route('/api/completion_funnel')
@admin_required
def api_completion_funnel():
    return jsonify(get_completion_funnel())

@admin_bp.route('/api/daywise_completion')
@admin_required
def api_daywise_completion():
    return jsonify(get_daywise_completion())

@admin_bp.route('/api/track_completion')
@admin_required
def api_track_completion():
    return jsonify(get_track_completion_stats())

@admin_bp.route('/api/problem_analytics')
@admin_required
def api_problem_analytics():
    return jsonify(get_problem_analytics())

@admin_bp.route('/api/submission_stats')
@admin_required
def api_submission_stats():
    return jsonify(get_submission_stats())

@admin_bp.route('/api/engagement')
@admin_required
def api_engagement():
    return jsonify(get_engagement_stats())

@admin_bp.route('/api/streak_leaderboard')
@admin_required
def api_streak_leaderboard():
    return jsonify(get_streak_leaderboard())

# ---------- Export routes ----------
@admin_bp.route('/export/<entity>')
@admin_required
def export_entity(entity):
    """Export data for a given entity as CSV (default) or Excel.
    Use query param ?format=excel for Excel.
    """
    try:
        df = get_export_data(entity)
    except ValueError as e:
        flash(str(e), 'danger')
        return redirect(url_for('admin.dashboard'))

    fmt = request.args.get('format', 'csv')
    if fmt == 'excel':
        output = df.to_excel(index=False, engine='openpyxl')
        mime = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        ext = 'xlsx'
    else:
        output = df.to_csv(index=False)
        mime = 'text/csv'
        ext = 'csv'
    return Response(
        output,
        mimetype=mime,
        headers={'Content-Disposition': f'attachment; filename={entity}_export.{ext}'}
    )
