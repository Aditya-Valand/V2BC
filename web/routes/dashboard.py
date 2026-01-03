from flask import Blueprint, render_template, redirect, url_for
from middlewares import token_required

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/dashboard', methods=['GET'])
@token_required
def dashboard(user_from_token):
    """
    Dashboard route using raw SQLite queries.
    """
    # 1. Fetch user data using your existing helper function
    user = get_user_by_email(user_from_token['email'])

    if not user:
        return redirect(url_for('auth.login'))

    # 2. Get Transaction Count (Using Raw SQL)
    # This is needed for the Digital Trust Score logic
    conn = get_db_connection()
    tx_row = conn.execute(
        'SELECT COUNT(*) as count FROM transactions WHERE user_id = ?',
        (user['id'],)
    ).fetchone()
    tx_count = tx_row['count'] if tx_row else 0
    conn.close()

    # 3. GATHER DATA FROM SERVICES

    # A. Compliance (Pass values from the SQLite Row dictionary)
    compliance_report = ComplianceEngine.validate_business(
        user['biz_type'],
        user['annual_turnover'],
        state=user['state']
    )

    # B. Tax Calculation
    tax_analysis = BusinessCalculator.calculate_presumptive_tax(user['annual_turnover'])

    # C. Credit Score Logic
    # Converting the SQLite Row to a dict so the Engine can read it easily
    user_dict = dict(user)
    credit_score, reasons = LoanEligibilityEngine.get_readiness_score(user_dict, tx_count)

    # 4. PACKAGE DATA FOR THE FRONTEND
    dashboard_data = {
        "profile": user, # This is the SQLite Row object
        "compliance": compliance_report,
        "tax": tax_analysis,
        "credit": {
            "score": credit_score,
            "reasons": reasons
        },
        "labour": {
            # Assuming your user table has 'avg_daily_wage' column
            "is_compliant": user['avg_daily_wage'] >= 190 if 'avg_daily_wage' in user.keys() else True,
            "gap": max(0, 190 - user['avg_daily_wage']) if 'avg_daily_wage' in user.keys() else 0
        }
    }

    return render_template('dashboard.html', data=dashboard_data)


@dashboard_bp.route('/profile', methods=['GET'])
@token_required
def profile(user):
    return render_template('profile.html')
