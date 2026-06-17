import os
import sys
# Add project root to PYTHONPATH so that local packages (e.g., utils) can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from supabase import create_client
from utils.auth import _hash_password
from dotenv import load_dotenv

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
)

# Get all students
students = (
    supabase.table("students")
    .select("id,email,password_hash")
    .execute()
    .data
)

updated = 0

for student in students:
    password = student.get("password_hash")
    # Skip if already an Argon2 hash
    if password and isinstance(password, str) and password.startswith("$argon2"):
        continue
    # If password is None or empty, skip (nothing to hash)
    if not password:
        continue
    new_hash = _hash_password(password)
    supabase.table("students").update({"password_hash": new_hash}).eq("id", student["id"]).execute()
    print(f"Updated: {student['email']}")
    updated += 1

print(f"\nMigration completed. {updated} accounts updated.")
