from argon2 import PasswordHasher

ph = PasswordHasher()

def _hash_password(pw: str) -> str:
    """Hash a plain-text password using Argon2."""
    return ph.hash(pw)

def _verify_password(pw: str, hashed: str) -> bool:
    """Verify a password against its Argon2 hash."""
    try:
        return ph.verify(hashed, pw)
    except Exception:
        return False
