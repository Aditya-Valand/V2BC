import sqlite3
from database.config import get_db_connection
from werkzeug.security import generate_password_hash, check_password_hash

def create_user(name, email, password):
    """Inserts a new user into the database."""
    conn = get_db_connection()
    hashed_password = generate_password_hash(password)
    conn.execute('''
        INSERT INTO users (name, email, password)
        VALUES (?, ?, ?);
    ''', (name, email, hashed_password))
    conn.commit()
    conn.close()

def verify_user(email, password):
    """Verifies user credentials."""
    conn = get_db_connection()
    hashed_password = conn.execute('''
        SELECT password FROM users WHERE email = ?;
    ''', (email,)).fetchone()
    conn.close()

    if hashed_password and check_password_hash(hashed_password['password'], password):
        return True
    return False

def get_user_by_email(email):
    """Fetches a user by email."""
    conn = get_db_connection()
    user = conn.execute('''
        SELECT * FROM users WHERE email = ?;
    ''', (email,)).fetchone()
    conn.close()
    return user
