from flask import Blueprint, render_template, request, redirect, url_for, flash
import os
from werkzeug.utils import secure_filename
from datetime import datetime

# Import your non-ORM database functions
from database.transaction import create_transaction, get_transactions_by_user
from services.document_ai import DocumentAI
from middlewares import token_required

transactions_bp = Blueprint('transactions', __name__)
ocr_tool = DocumentAI()

# Configure where to store uploaded bill images
UPLOAD_FOLDER = 'web/static/uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@transactions_bp.route('/transactions')
@token_required
def list_transactions(user):
    """Shows history of all scanned bills."""
    records = get_transactions_by_user(user['id'])
    return render_template('transactions_list.html', transactions=records)

@transactions_bp.route('/scan', methods=['POST'])
@token_required
def scan_bill(user):
    """Processes the image and sends data to the review form."""
    if 'bill_image' not in request.files:
        flash("Please select a file first!", "warning")
        return redirect(url_for('dashboard.dashboard'))

    file = request.files['bill_image']
    if file.filename == '':
        return redirect(url_for('dashboard.dashboard'))

    # Save the file securely
    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    # Trigger your DocumentAI pipeline
    extracted_data = ocr_tool.extract_data(filepath)
    
    # Add the current date if OCR failed to find it
    if not extracted_data.get('date'):
        extracted_data['date'] = datetime.now().strftime('%Y-%m-%d')

    # Pass the AI results to the 'Add Transaction' page for user verification
    return render_template('add_transaction.html', data=extracted_data)

@transactions_bp.route('/save', methods=['POST'])
@token_required
def save_transaction(user):
    """Final step: User confirms the data and we save it to SQLite."""
    try:
        # Get data from the form (which was pre-filled by AI)
        amount = float(request.form.get('amount', 0))
        category = request.form.get('category', 'General')
        merchant = request.form.get('merchant', 'Unknown')
        date = request.form.get('date')
        gstin = request.form.get('gstin')

        # Use your database/transaction.py function
        create_transaction(
            user_id=user['id'],
            amount=amount,
            category=category,
            merchant=merchant,
            date=date,
            gstin=gstin,
            is_verified=1
        )
        flash("Bill saved and logged successfully!", "success")
    except Exception as e:
        flash(f"Error saving transaction: {str(e)}", "danger")
    
    return redirect(url_for('dashboard.dashboard'))