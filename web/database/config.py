import sqlite3
from werkzeug.security import generate_password_hash

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
    # seed_demo_data()
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


def seed_demo_data():
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Clear existing data to avoid UNIQUE constraints errors during demo
    cursor.execute("DELETE FROM business_profiles")
    cursor.execute("DELETE FROM transactions")
    cursor.execute("DELETE FROM users")

    # 2. Create the Primary User (Sarah Connor - Freelancer/Cafe Owner)
    # Using the name/role from your dashboard UI screenshot
    hashed_pw = generate_password_hash("password123")
    cursor.execute('''
        INSERT INTO users (name, email, password, profile)
        VALUES (?, ?, ?, ?)
    ''', ("Sarah Connor", "a7952534@gmail.com", hashed_pw, 1))

    user_id = cursor.lastrowid

    # 3. Create a High-Compliance Business Profile
    # This setup ensures the dashboard shows "Secure" legal status
    cursor.execute('''
        INSERT INTO business_profiles (
            user_id, business_type, legal_structure, business_name,
            commencement_date, employees_count, state, district,
            mode_of_sales, annual_turnover, nature_of_income,
            income_frequency, existing_loans, pan_available,
            gstin_available, udyam_registered, business_bank_account,
            digital_payments_enabled, previous_itr_filed
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_id, 'Services', 'Sole Proprietorship', 'Connor Cafe & Tech',
        '2024-01-01', 2, 'Maharashtra', 'Mumbai',
        'Omnichannel', 2400000, 'Business',
        'Daily', 'None', 1,
        1, 1, 1, 1, 1
    ))

    # 4. Insert Strategic Transactions
    # This triggers the Tax Liability (₹12,450) and Loan Power (85/100)
    transactions = [
        # High value inventory - helps lower tax liability
        (user_id, 15000.0, 'Inventory', 'Super-Gas Appliances', '2026-01-01', '27AAAAA0000A1Z5', 1),
        # Compliant Salary - triggers the "Labour Wages Compliant" badge
        (user_id, 12000.0, 'Salary', 'Staff Payment', '2026-01-02', None, 1),
        # Marketing expense
        (user_id, 5000.0, 'Marketing', 'Instagram Ads', '2026-01-03', None, 1),
        # Raw materials with GST - demonstrates Input Tax Credit potential
        (user_id, 8500.0, 'Stock', 'Reliance Retail', '2026-01-03', '27AAACR1234A1Z1', 1)
    ]

    cursor.executemany('''
        INSERT INTO transactions (user_id, amount, category, merchant, date, gstin, is_verified)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', transactions)

    conn.commit()
    conn.close()
    print("✅ Demo Data Seeded Successfully!")
    print("User: a7952534@gmail.com | Pass: password123")
