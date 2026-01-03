from flask import Blueprint, render_template, redirect, url_for, request, jsonify
from database.user import get_user_by_email, save_business_profile, get_business_profile
from database.config import get_db_connection # Import your connection helper
from services.rule_engine import ComplianceEngine
from services.calculator import BusinessCalculator
from services.rule_engine import LoanEligibilityEngine
from middlewares import token_required

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/dashboard', methods=['GET'])
@token_required
def dashboard(user):
    """
    Dashboard route using raw SQLite queries.
    """
    # 1. Fetch user data using your existing helper function


    # 2. Get Transaction Count (Using Raw SQL)
    # This is needed for the Digital Trust Score logic
    # conn = get_db_connection()
    # tx_row = conn.execute(
    #     'SELECT COUNT(*) as count FROM transactions WHERE user_id = ?',
    #     (user['id'],)
    # ).fetchone()
    # tx_count = tx_row['count'] if tx_row else 0
    # conn.close()

    # # 3. GATHER DATA FROM SERVICES

    # # A. Compliance (Pass values from the SQLite Row dictionary)
    # compliance_report = ComplianceEngine.validate_business(
    #     user['biz_type'],
    #     user['annual_turnover'],
    #     state=user['state']
    # )

    # # B. Tax Calculation
    # tax_analysis = BusinessCalculator.calculate_presumptive_tax(user['annual_turnover'])

    # # C. Credit Score Logic
    # # Converting the SQLite Row to a dict so the Engine can read it easily
    # user_dict = dict(user)
    # credit_score, reasons = LoanEligibilityEngine.get_readiness_score(user_dict, tx_count)

    # # 4. PACKAGE DATA FOR THE FRONTEND
    # dashboard_data = {
    #     "profile": user, # This is the SQLite Row object
    #     "compliance": compliance_report,
    #     "tax": tax_analysis,
    #     "credit": {
    #         "score": credit_score,
    #         "reasons": reasons
    #     },
    #     "labour": {
    #         # Assuming your user table has 'avg_daily_wage' column
    #         "is_compliant": user['avg_daily_wage'] >= 190 if 'avg_daily_wage' in user.keys() else True,
    #         "gap": max(0, 190 - user['avg_daily_wage']) if 'avg_daily_wage' in user.keys() else 0
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
