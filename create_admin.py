import os
from database.supabase_client import supabase
from utils.auth import _hash_password

def create_admin(email, name, password):
    hashed_pw = _hash_password(password)
    
    # Check if exists
    existing = supabase.from_("admins").select("id").eq("email", email).execute().data
    if existing:
        print(f"Admin with email {email} already exists.")
        return
        
    data = {
        "email": email,
        "name": name,
        "password_hash": hashed_pw
    }
    
    try:
        supabase.from_("admins").insert(data).execute()
        print(f"Successfully created admin account: {email}")
    except Exception as e:
        print(f"Error creating admin: {e}")

if __name__ == "__main__":
    create_admin("admin@example.com", "System Admin", "admin123")
