from functools import wraps
from flask import session, redirect, url_for, flash
from database.supabase_client import supabase

def admin_required(view_func):
    """Simple admin guard.
    Expects the user's record to have an `is_admin` boolean column.
    The flag is cached in the session on login (not shown here).
    If not present, fetch from Supabase.
    """
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access admin pages.", "warning")
            return redirect(url_for("auth.login"))
        # Try session cache first
        if session.get("is_admin") is True:
            return view_func(*args, **kwargs)
        # Fallback: fetch from DB
        user_id = session.get("user_id")
        try:
            result = supabase.from_("students").select("is_admin").eq("id", user_id).single().execute()
            is_admin = result.data.get("is_admin", False) if result.data else False
        except Exception:
            is_admin = False
        if not is_admin:
            flash("Admin privileges required.", "danger")
            return redirect(url_for("main.dashboard"))
        # Cache for the session
        session["is_admin"] = True
        return view_func(*args, **kwargs)
    return wrapper
