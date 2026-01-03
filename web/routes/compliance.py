from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from database.user import get_user_by_email
from database.user import get_full_user_profile
from database.config import get_db_connection
from services.rule_engine import ComplianceEngine
from services.calculator import BusinessCalculator
from middlewares import token_required
import os

compliance_bp = Blueprint('compliance', __name__)

@compliance_bp.route('/check-wages', methods=['POST'])
@token_required
def check_wages(user):
    """
    Handles raw SQL update for employee wages and runs the 2026 Floor Wage check.
    """
    daily_wage = float(request.form.get('daily_wage', 0))

    # 1. Update the database using raw SQL
    conn = get_db_connection()
    conn.execute(
        'UPDATE users SET avg_daily_wage = ? WHERE id = ?',
        (daily_wage, user['id'])
    )
    conn.commit()
    conn.close()

    # 2. Use the Calculator service to verify compliance
    # Projected 2026 National Floor Wage: ₹190
    wage_status = BusinessCalculator.check_floor_wage_compliance(daily_wage, user['state'])

    if not wage_status['is_compliant']:
        flash(f"⚠️ Warning: Wage is below statutory limit (₹{wage_status['required']}). Gap: ₹{wage_status['gap']}", "danger")
    else:
        flash("✅ Your business is compliant with 2026 Labour Codes.", "success")

    return redirect(url_for('dashboard.dashboard'))

@compliance_bp.route('/tax-planner')
@token_required
def tax_planner(user):
    """
    Gathers detailed tax data for the ITR-4 (Sugam) 2026 planner.
    """

    # Calculate Presumptive Tax savings
    tax_data = BusinessCalculator.calculate_presumptive_tax(user['annual_turnover'])

    # Get the 4-step Advance Tax schedule (June, Sept, Dec, March)
    advance_tax = BusinessCalculator.get_advance_tax_schedule(tax_data['tax_due'])

    return render_template('tax_planner.html',
                           tax=tax_data,
                           schedule=advance_tax,
                           user=user)

@compliance_bp.route('/fssai-status')
@token_required
def fssai_status(user):
    """
    Determines mandatory FSSAI license tiers based on turnover.
    """

    # Logic for tiered licensing (Basic vs State vs Central)
    fssai_details = BusinessCalculator.get_fssai_details(user['annual_turnover'])

    return render_template('fssai_details.html', fssai=fssai_details, user=user)


# web/routes/compliance.py

@compliance_bp.route('/tax-calendar')
@token_required
def tax_calendar(user):
    """
    Provides a dynamic tax filing calendar based on business profile.
    """
    # 1. Fetch full user and business profile data
    raw_user = get_full_user_profile(user['email'])
    if not raw_user:
        return redirect(url_for('auth.login'))
    
    user_dict = dict(raw_user)
    
    # 2. Gather necessary transactional data for Wage Compliance
    conn = get_db_connection()
    tx_rows = conn.execute('SELECT * FROM transactions WHERE user_id = ?', (user_dict['id'],)).fetchall()
    salary_txs = [tx for tx in tx_rows if tx['category'] == 'Salary']
    total_salary_paid = sum(tx['amount'] for tx in salary_txs)
    tx_count = len(tx_rows)
    conn.close()

    # 3. Calculate Labour Data
    emp_count = user_dict.get('employees_count', 1)
    avg_daily_wage = total_salary_paid / (emp_count * 26) if emp_count > 0 and total_salary_paid > 0 else 0
    
    labour_data = {
        "current_wage": round(avg_daily_wage, 2),
        "min_required": 190, # 2026 Floor Wage
        "is_compliant": avg_daily_wage >= 190 or emp_count == 0
    }

    # 4. Generate the Advance Tax Schedule
    tax_analysis = BusinessCalculator.calculate_presumptive_tax(user_dict.get('annual_turnover', 0))

    # 5. Package everything into the 'user' variable expected by the template
    dashboard_data = {
        "profile": user_dict,
        "labour": labour_data,
        "tax": tax_analysis
    }

    return render_template('tax_calendar.html', user=dashboard_data)