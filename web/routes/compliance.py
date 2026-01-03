from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from datetime import datetime, date
from web.models.transaction import Transaction
from web.models.user import User
from web.services.rule_engine import ComplianceEngine
from web.services.calculator import BusinessCalculator
from web.services.loan_engine import LoanEligibilityEngine
from web.services.document_ai import DocumentAI
import os

compliance_bp = Blueprint('compliance', __name__)
ocr_tool = DocumentAI()

@compliance_bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user = User.query.get(session['user_id'])
    
    # 1. CORE COMPLIANCE & 2026 LABOUR REFORMS
    # Includes new Social Security Fund logic (1-2% for Gig workers)
    compliance = ComplianceEngine.validate_business(
        user.biz_type, 
        user.annual_turnover,
        state=user.state
    )

    # 2. INCOME TAX & ADVANCE TAX TRACKING
    # Calculates presumptive tax (ITR-4) and checks for Advance Tax installments
    tax_data = BusinessCalculator.calculate_presumptive_tax(user.annual_turnover)
    advance_tax_schedule = BusinessCalculator.get_advance_tax_deadlines(tax_data['tax_due'])

    # 3. FSSAI & LICENSE MANAGEMENT
    # Determines FSSAI category (Basic/State/Central) and renewal costs
    fssai_info = BusinessCalculator.get_fssai_details(user.annual_turnover, user.biz_type)

    # 4. CREDIT READINESS SCORECARD
    tx_count = Transaction.query.filter_by(user_id=user.id).count()
    credit_score, reasons = LoanEligibilityEngine.get_readiness_score(
        {"has_udyam": user.has_udyam, "has_itr": user.has_itr, "has_gst": user.has_gst},
        tx_count
    )

    # 5. RECOMMENDED GOVT SCHEMES (MUDRA, SVANidhi, etc.)
    loans = LoanEligibilityEngine.recommend_schemes(
        {"biz_type": user.biz_type, "annual_turnover": user.annual_turnover, "is_special_category": user.is_special_category},
        credit_score
    )

    return render_template('dashboard.html', 
                           user=user, 
                           compliance=compliance, 
                           tax_data=tax_data,
                           advance_tax=advance_tax_schedule,
                           fssai=fssai_info,
                           credit_score=credit_score,
                           reasons=reasons,
                           loans=loans)

@compliance_bp.route('/check-wages', methods=['POST'])
def check_wages():
    """
    New 2026 Feature: Floor Wage Compliance.
    Ensures employees are paid at or above the statutory floor wage.
    """
    daily_wage = float(request.form.get('daily_wage'))
    # Thresholds typically updated by state/central govt
    is_compliant = daily_wage >= 178.0 # Example National Floor Wage
    
    if not is_compliant:
        flash("⚠️ Wage Alert: This is below the National Floor Wage. Correct it to avoid penalties.", "danger")
    else:
        flash("✅ Compliant: Wage meets or exceeds statutory standards.", "success")
    
    return redirect(url_for('compliance.dashboard'))

@compliance_bp.route('/upload-invoice', methods=['POST'])
def upload_invoice():
    if 'invoice' not in request.files:
        flash("No file selected")
        return redirect(url_for('compliance.dashboard'))

    file = request.files['invoice']
    path = os.path.join('web/static/uploads', file.filename)
    file.save(path)

    # OCR extraction for automatic paperwork reduction
    extracted_data = ocr_tool.extract_data(path)

    return render_template('add_transaction.html', data=extracted_data)