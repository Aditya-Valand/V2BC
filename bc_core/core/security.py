"""
Password hashing utilities.

Uses the `bcrypt` library directly (bypasses passlib which has known
compatibility issues with bcrypt 4.x).
"""
import bcrypt


def hash_password(password: str) -> str:
    """Hash a plaintext password. Returns a UTF-8 string suitable for DB storage."""
    # bcrypt has a hard limit of 72 bytes; enforce it explicitly
    encoded = password.encode("utf-8")[:72]
    return bcrypt.hashpw(encoded, bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Return True if the plaintext password matches the stored hash."""
    try:
        return bcrypt.checkpw(
            password.encode("utf-8")[:72],
            hashed.encode("utf-8"),
        )
    except Exception:
        return False
