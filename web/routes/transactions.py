from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
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
    return render_template('transactions_list.html', transactions=records)

@transactions_bp.route('/scan', methods=['POST'])
@token_required
def scan_bill(user):
    """Step 1: Receive image and run Gemini Vision OCR."""
    if 'bill_image' not in request.files:
        flash("No file detected. Please capture or upload a bill.", "warning")
        return redirect(url_for('dashboard.dashboard'))

    file = request.files['bill_image']
    if file.filename == '':
        return redirect(url_for('dashboard.dashboard'))

    # 1. Setup Absolute Path for Saving
    upload_base = os.path.join(current_app.root_path, 'static', 'uploads')
    if not os.path.exists(upload_base):
        os.makedirs(upload_base)

    # 2. Secure and Save the File
    filename = secure_filename(file.filename)
    unique_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
    absolute_filepath = os.path.join(upload_base, unique_filename)
    file.save(absolute_filepath)

    try:
        # 3. Trigger Gemini pipeline with the ABSOLUTE path
        extracted_data = ocr_tool.extract_data(absolute_filepath)
        raw_date = extracted_data.get('invoice_date', '')
        formatted_date = ""
        if raw_date:
            try:
                # Try to parse the specific format Gemini returned: 28/8/19
                parsed_date = datetime.strptime(raw_date, "%d/%m/%y")
                # Convert it to the HTML required format: 2019-08-28
                formatted_date = parsed_date.strftime("%Y-%m-%d")
            except ValueError:
                # Fallback to current date if parsing fails
                formatted_date = datetime.now().strftime('%Y-%m-%d')
        else:
            formatted_date = datetime.now().strftime('%Y-%m-%d')

        # 4. Map data for the Review Form (add_transaction.html)
        formatted_data = {
            "merchant": extracted_data.get('vendor_name'),
            "amount": extracted_data.get('total_amount'),
            "date": formatted_date,
            "gstin": extracted_data.get('gstin'),
            "invoice_no": extracted_data.get('invoice_number'),
            "file_url": f"uploads/{unique_filename}" 
        }

        # Fallback date if AI fails to find one
        

        # 5. RENDER REVIEW FORM - Do not redirect yet!
        # This allows the user to click "Save" which triggers transactions.save_transaction
        return render_template('add_transaction.html', data=formatted_data)

    except Exception as e:
        # If AI fails, we still have the file saved, but we return to dashboard
        flash(f"AI Extraction failed: {str(e)}", "danger")
        return redirect(url_for('dashboard.dashboard'))

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
    
    return redirect(url_for('dashboard.dashboard'))

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