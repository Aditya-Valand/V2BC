from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
import os
from werkzeug.utils import secure_filename
from datetime import datetime

# Import your non-ORM database functions
from database.transaction import create_transaction, get_transactions_by_user
from services.document_ai import DocumentAI
from middlewares import token_required

transactions_bp = Blueprint('transactions', __name__)

# Initialize your new Gemini-based OCR tool
# Ensure GOOGLE_API_KEY is set in your environment variables
ocr_tool = DocumentAI()
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER,exist_ok=True)

@transactions_bp.route('/transactions')
@token_required
def list_transactions(user):
    """Shows history of all scanned bills using the joined user ID."""
    records = get_transactions_by_user(user['id'])
    return render_template('transactions_list.html', transactions=records, user=user)

@transactions_bp.route('/scan', methods=['POST'])
@token_required
def scan_bill(user):
    """Step 1: Receive image and run Gemini Vision OCR."""
    try:
        # 1. VALIDATION: Check file existence
        if 'bill_image' not in request.files:
            return jsonify({"success": False, "message": "No file detected"}), 400

        file = request.files['bill_image']

        # 2. VALIDATION: Check filename
        if file.filename == '':
            return jsonify({"success": False, "message": "No file selected"}), 400

        # 3. Secure and Save
        upload_base = os.path.join(current_app.root_path, 'static', 'uploads')
        if not os.path.exists(upload_base):
            os.makedirs(upload_base)

        filename = secure_filename(file.filename)
        # Use timestamp to prevent filename collisions
        unique_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
        absolute_filepath = os.path.join(upload_base, unique_filename)
        file.save(absolute_filepath)

        # 4. Trigger Gemini OCR
        # We assume ocr_tool handles its own internal errors, but we wrap in try/except just in case
        extracted_data = ocr_tool.extract_data(absolute_filepath)

        # 5. Date Parsing Logic
        raw_date = extracted_data.get('invoice_date', '')
        formatted_date = datetime.now().strftime('%Y-%m-%d') # Default fallback

        if raw_date:
            try:
                # Attempt to parse DD/MM/YY format common in invoices
                parsed_date = datetime.strptime(raw_date, "%d/%m/%y")
                formatted_date = parsed_date.strftime("%Y-%m-%d")
            except ValueError:
                # Keep default if parsing fails
                pass

        # 6. Prepare Data for the Form
        formatted_data = {
            "merchant": extracted_data.get('vendor_name', ''),
            "amount": extracted_data.get('total_amount', 0),
            "date": formatted_date,
            "gstin": extracted_data.get('gstin', ''),
            "invoice_no": extracted_data.get('invoice_number', ''),
            "file_url": f"uploads/{unique_filename}"
        }

        # 7. SUCCESS: Render the Template (HTML)
        # This "redirects" the user to the review page with data pre-filled
        return render_template('add_transaction.html', data=formatted_data, user=user)

    except Exception as e:
        # 8. FAILURE: Catch-all error returning JSON
        print(f"OCR Error: {e}") # Log it for debugging
        return jsonify({"success": False, "message": "Failed to process image. Please try again."}), 500

@transactions_bp.route('/save', methods=['POST'])
@token_required
def save_transaction(user):
    """Step 2: Save the AI-extracted data after user verification."""
    try:
        create_transaction(
            user_id=user['id'], # ID from the joined business_profiles table
            amount=float(request.form.get('amount', 0)),
            category=request.form.get('category', 'Inventory'),
            merchant=request.form.get('merchant', 'Unknown'),
            date=request.form.get('date'),
            gstin=request.form.get('gstin'),
            is_verified=1
        )
        flash("Transaction successfully audited and saved!", "success")
    except Exception as e:
        flash(f"Database Error: {str(e)}", "danger")

    return redirect(url_for('transactions.list_transactions'))

@transactions_bp.route('/debug-last-scan/<filename>')
@token_required
def debug_last_scan(user, filename):
    """Temporary route to see raw AI output for a specific file."""
    import os
    from flask import jsonify, current_app

    filepath = os.path.join(current_app.root_path, 'static', 'uploads', filename)

    try:
        # Run the extraction
        raw_data = ocr_tool.extract_data(filepath)

        # Return raw JSON to the browser
        return jsonify({
            "status": "success",
            "filename": filename,
            "extracted_data": raw_data
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
