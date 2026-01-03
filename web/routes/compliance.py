from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from database.user import get_user_by_email
from database.config import get_db_connection
from services.rule_engine import ComplianceEngine
from services.calculator import BusinessCalculator
from middlewares import token_required
import os

compliance_bp = Blueprint('compliance', __name__)

@compliance_bp.route('/check-wages', methods=['POST'])
@token_required
def check_wages(user_from_token):
    """
    Handles raw SQL update for employee wages and runs the 2026 Floor Wage check.
    """
    daily_wage = float(request.form.get('daily_wage', 0))
    user = get_user_by_email(user_from_token['email'])
    
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
def tax_planner(user_from_token):
    """
    Gathers detailed tax data for the ITR-4 (Sugam) 2026 planner.
    """
    user = get_user_by_email(user_from_token['email'])
    
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
def fssai_status(user_from_token):
    """
    Determines mandatory FSSAI license tiers based on turnover.
    """
    user = get_user_by_email(user_from_token['email'])
    
    # Logic for tiered licensing (Basic vs State vs Central)
    fssai_details = BusinessCalculator.get_fssai_details(user['annual_turnover'])
    
    return render_template('fssai_details.html', fssai=fssai_details, user=user)