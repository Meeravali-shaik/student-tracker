from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from database.supabase_client import supabase
from utils.auth import _verify_password, _hash_password

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        
        # Check students
        user = supabase.from_("students").select("*").eq("email", email).execute().data
        role = "student"
        
        if not user:
            # Check admins
            user = supabase.from_("admins").select("*").eq("email", email).execute().data
            role = "admin"
            
        if user and _verify_password(password, user[0]["password_hash"]):
            session["user_id"] = user[0]["id"]
            session["role"] = role
            session["name"] = user[0]["name"]
            session["email"] = user[0]["email"]
            flash(f"Welcome back, {user[0]['name']}!", "success")
            if role == "admin":
                return redirect(url_for("admin.dashboard"))
            return redirect(url_for("main.dashboard"))
        else:
            flash("Invalid email or password", "error")
            
    return render_template("login.html")

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        
        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return redirect(url_for("auth.register"))
            
        # Check if email already exists
        existing_student = supabase.from_("students").select("id").eq("email", email).execute().data
        existing_admin = supabase.from_("admins").select("id").eq("email", email).execute().data
        
        if existing_student or existing_admin:
            flash("Email already registered. Please log in.", "error")
            return redirect(url_for("auth.login"))
            
        # Create new student
        data = {
            "name": name,
            "email": email,
            "password_hash": _hash_password(password)
        }
        
        try:
            supabase.from_("students").insert(data).execute()
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for("auth.login"))
        except Exception as e:
            flash("An error occurred during registration. Please try again.", "error")
            
    return render_template("register.html")

@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
