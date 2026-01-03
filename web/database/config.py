import sqlite3

# All database-related functions are defined here.

def get_db_connection():
    conn = sqlite3.connect('./database/project_database.sqlite')
    # This allows us to access data by column name: user['name']
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Creates the table if it doesn't exist yet."""
    conn = get_db_connection()
    conn.execute(users_table())
    conn.execute(profiles_table())
    conn.commit()
    conn.close()

def users_table():
    return """CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        password TEXT NOT NULL,
        profile NUMERIC DEFAULT 0,
        token TEXT,
        status TEXT DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );"""


def profiles_table():
    return """CREATE TABLE IF NOT EXISTS profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        bio TEXT,
        avatar_url TEXT,
        FOREIGN KEY (user_id) REFERENCES users (id)
    );"""
