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
    conn.execute(transactions_table())
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
    return """CREATE TABLE IF NOT EXISTS business_profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL UNIQUE,
        business_type TEXT NOT NULL,
        legal_structure TEXT NOT NULL,
        business_name TEXT NOT NULL,
        commencement_date DATE NOT NULL,
        employees_count NUMBER NOT NULL,
        state TEXT NOT NULL,
        district TEXT NOT NULL,
        mode_of_sales TEXT NOT NULL,
        annual_turnover INTEGER NOT NULL,
        nature_of_income TEXT NOT NULL,
        income_frequency TEXT NOT NULL,
        existing_loans TEXT NOT NULL,
        pan_available INTEGER DEFAULT 0,
        gstin_available INTEGER DEFAULT 0,
        udyam_registered INTEGER DEFAULT 0,
        business_bank_account INTEGER DEFAULT 0,
        digital_payments_enabled INTEGER DEFAULT 0,
        previous_itr_filed INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    );"""

def transactions_table():
    return """CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        category TEXT NOT NULL,      -- e.g., 'Inventory', 'Salary', 'Rent'
        merchant TEXT,               -- Extracted Vendor Name
        date TEXT NOT NULL,          -- Format: YYYY-MM-DD
        gstin TEXT,                  -- 15-digit Indian GST Number
        is_verified INTEGER DEFAULT 0, -- 1 if the user confirmed the AI extraction
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    );"""