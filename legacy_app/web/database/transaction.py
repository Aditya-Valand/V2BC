import sqlite3
from database.config import get_db_connection

def create_transaction(user_id, amount, category, merchant, date, gstin=None, is_verified=0):
    """Logs a new transaction, often called after Document AI (OCR) processing."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO transactions (user_id, amount, category, merchant, date, gstin, is_verified)
        VALUES (?, ?, ?, ?, ?, ?, ?);
    ''', (user_id, amount, category, merchant, date, gstin, is_verified))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id

def get_transactions_by_user(user_id):
    """Fetches all records for a specific user to power the Dashboard & Trust Score."""
    conn = get_db_connection()
    transactions = conn.execute('''
        SELECT * FROM transactions
        WHERE user_id = ?
        ORDER BY date DESC;
    ''', (user_id,)).fetchall()
    conn.close()
    return transactions

def get_transaction_stats(user_id):
    """Calculates totals needed for 'Smart Financial Snapshots' on the dashboard."""
    conn = get_db_connection()
    stats = conn.execute('''
        SELECT
            SUM(amount) as total_spent,
            COUNT(*) as tx_count,
            COUNT(DISTINCT category) as category_count
        FROM transactions
        WHERE user_id = ?;
    ''', (user_id,)).fetchone()
    conn.close()
    return stats

def delete_transaction(transaction_id, user_id):
    """Allows users to remove a mistakenly scanned bill."""
    conn = get_db_connection()
    conn.execute('''
        DELETE FROM transactions WHERE id = ? AND user_id = ?;
    ''', (transaction_id, user_id))
    conn.commit()
    conn.close()
