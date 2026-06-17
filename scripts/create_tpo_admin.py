# scripts/create_tpo_admin.py
"""Create a TPO admin account in Supabase.
Usage:
    python scripts/create_tpo_admin.py
It will insert a new admin row with email and password (hashed with Argon2).
If an admin with the same email already exists, it skips creation.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from supabase import create_client, Client
from utils.auth import _hash_password

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Supabase credentials not set in .env")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# TPO admin credentials – change as needed
ADMIN_EMAIL = "tpo@example.com"
ADMIN_NAME = "TPO"
ADMIN_PASSWORD = "ChangeMe123!"

# Hash the password using Argon2 (same function used for students)
password_hash = _hash_password(ADMIN_PASSWORD)

# Check if admin already exists
existing = supabase.from_("admins").select("id").eq("email", ADMIN_EMAIL).execute().data
if existing:
    print(f"Admin with email {ADMIN_EMAIL} already exists. No action taken.")
else:
    data = {
        "name": ADMIN_NAME,
        "email": ADMIN_EMAIL,
        "password_hash": password_hash,
        # Optional: flag to distinguish TPO – can be added later
    }
    result = supabase.from_("admins").insert(data).execute()
    # Check for insertion errors
    if getattr(result, "error", None) or getattr(result, "status_code", None) != 201:
        # Print detailed error info if available
        err = getattr(result, "error", None)
        if err:
            print("Error creating admin:", err)
        else:
            print("Error creating admin: status code", getattr(result, "status_code", "unknown"))
    else:
        print(f"Admin {ADMIN_EMAIL} created successfully.")
