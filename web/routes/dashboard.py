from flask import Blueprint, render_template, redirect, url_for, request, jsonify
from database.user import get_user_by_email, save_business_profile, get_business_profile, user_profile_status_update,get_full_user_profile
from database.config import get_db_connection # Import your connection helper
from services.rule_engine import ComplianceEngine
from services.calculator import BusinessCalculator
from services.rule_engine import LoanEligibilityEngine
from middlewares import token_required

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/dashboard', methods=['GET'])
@token_required
def dashboard(user):
    # # 1. Fetch combined data using the new JOIN function
    # user = get_full_user_profile(user['email'])
    
    # if not user:
    #     return redirect(url_for('auth.login'))

    # # 2. Get Transaction Count (for Digital Trust Score)
    # conn = get_db_connection()
    # tx_row = conn.execute(
    #     'SELECT COUNT(*) as count FROM transactions WHERE user_id = ?',
    #     (user['id'],)
    # ).fetchone()
    # tx_count = tx_row['count'] if tx_row else 0
    # conn.close()

    # # 3. GATHER DATA FROM SERVICES
    # # Map the new table column names correctly
    # biz_type = user['business_type'] if user['business_type'] else "General"
    # turnover = user['annual_turnover'] if user['annual_turnover'] else 0
    # state = user['state'] if user['state'] else "General"

    # # A. Compliance Checklist
    # compliance_report = ComplianceEngine.validate_business(biz_type, turnover, state=state)

    # # B. Tax & Savings Analysis
    # tax_analysis = BusinessCalculator.calculate_presumptive_tax(turnover)

    # # C. Credit Readiness (Digital Trust)
    # # Map Integer booleans (0/1) to Python Booleans
    # readiness_data = {
    #     "has_udyam": bool(user['udyam_registered']),
    #     "has_itr": bool(user['previous_itr_filed']),
    #     "has_gst": bool(user['gstin_available'])
    # }
    # credit_score, reasons = LoanEligibilityEngine.get_readiness_score(readiness_data, tx_count)

    # # 4. PACKAGE DATA FOR FRONTEND
    # dashboard_data = {
    #     "profile": user,
    #     "compliance": compliance_report,
    #     "tax": tax_analysis,
    #     "credit": {
    #         "score": credit_score,
    #         "reasons": reasons
    #     },
    #     "labour": {
    #         # 2026 Floor Wage Check (Projected ₹190)
    #         "is_compliant": (user['employees_count'] or 0) == 0 or (user.get('avg_daily_wage', 0) >= 190),
    #         "gap": max(0, 190 - (user.get('avg_daily_wage', 0)))
    #     }
    # }

    return render_template('dashboard.html')


@dashboard_bp.route('/profile', methods=['GET', 'POST'])
@token_required
def profile(user):

    if user['profile'] == 1: # Profile complete
        return redirect(url_for('dashboard.dashboard'))

    if request.method == 'POST':
        # 1. Get the JSON data from Alpine.js
        data = request.get_json()

        if not data:
            return jsonify({"success": False, "message": "No data received"}), 400

        try:
            # 2. Save/Update the profile in the DB
            # 'user' is the dictionary returned by your token_required decorator
            save_business_profile(user['id'], data)
            user_profile_status_update(user['email'])

            # 3. Return success and the redirect URL
            return jsonify({
                "success": True,
                "message": "Profile updated successfully!",
                "redirect": url_for('dashboard.dashboard')
            }), 200

        except Exception as e:
            print(f"Error saving profile: {e}")
            return jsonify({"success": False, "message": "Database error"}), 500

    # GET request: Fetch existing data to pre-fill the form (optional)
    # existing_profile = get_business_profile(user['id'])
    return render_template('profile.html')


@dashboard_bp.route('/profile-json', methods=['GET'])
@token_required
def profile_json(user):
    """
    Provides the business profile data in JSON format for Alpine.js.
    """
    profile_data = get_business_profile(user['id'])
    if profile_data:
        # Convert Row object to dictionary
        profile_dict = dict(profile_data)
        return jsonify({"success": True, "data": profile_dict}), 200
    else:
        return jsonify({"success": False, "message": "Profile not found"}), 404
