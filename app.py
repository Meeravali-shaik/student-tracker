from flask import Flask, redirect, url_for, session, render_template
from flask_session import Session
import os

from routes.auth import auth_bp
from routes.main import main_bp
from routes.admin import admin_bp

app = Flask(__name__)

# Security
app.config["SECRET_KEY"] = os.getenv(
    "SECRET_KEY",
    "super-secret-key-2026"
)

# Session Configuration
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = os.path.join(
    app.root_path,
    ".flask_session"
)

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_USE_SIGNER"] = True

# Create session directory if missing
os.makedirs(
    app.config["SESSION_FILE_DIR"],
    exist_ok=True
)

Session(app)

# Register Blueprints
app.register_blueprint(auth_bp, url_prefix="/auth")
app.register_blueprint(main_bp, url_prefix="/")
app.register_blueprint(admin_bp, url_prefix="/admin")


@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("main.dashboard"))

    return redirect(url_for("auth.login"))


@app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_error(error):
    return render_template("500.html"), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
