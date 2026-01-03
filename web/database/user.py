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

def save_business_profile(user_id, data):
    """Inserts or updates a business profile for a specific user."""
    conn = get_db_connection()

    # We use REPLACE INTO because user_id is UNIQUE.
    # If a record exists for this user, it updates; otherwise, it inserts.
    conn.execute('''
        REPLACE INTO business_profiles (
            user_id, business_type, legal_structure, business_name,
            commencement_date, employees_count, state, district,
            mode_of_sales, annual_turnover, nature_of_income,
            income_frequency, existing_loans, pan_available,
            gstin_available, udyam_registered, business_bank_account,
            digital_payments_enabled, previous_itr_filed
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    ''', (
        user_id,
        data.get('business_type'),
        data.get('legal_structure'),
        data.get('business_name'),
        data.get('commencement_date'),
        data.get('employees_count'),
        data.get('state'),
        data.get('district'),
        data.get('mode_of_sales'),
        data.get('annual_turnover'),
        data.get('nature_of_income'),
        data.get('income_frequency'),
        data.get('existing_loans'),
        1 if data.get('pan_available') == 'Yes' else 0,
        1 if data.get('gstin_available') == 'Yes' else 0,
        1 if data.get('udyam_registered') == 'Yes' else 0,
        1 if data.get('business_bank_account') == 'Yes' else 0,
        1 if data.get('digital_payments_enabled') == 'Yes' else 0,
        1 if data.get('previous_itr_filed') == 'Yes' else 0
    ))
    conn.commit()
    conn.close()

def get_business_profile(user_id):
    """Fetches the business profile for a specific user."""
    conn = get_db_connection()
    profile = conn.execute('''
        SELECT * FROM business_profiles WHERE user_id = ?;
    ''', (user_id,)).fetchone()
    conn.close()
    return profile
