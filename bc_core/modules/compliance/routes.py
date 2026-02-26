"""
CA (Chartered Accountant) compliance and risk visibility endpoints.

Phase-3 Architecture:
- Routes are presentation only (no compliance logic)
- All logic delegated to ComplianceService
- Returns compliance signals, profiles, and alerts
- Dashboards show risk indicators and actionable intelligence

Strictly follows separation of concerns:
✓ Routes = presentation, queries, authentication
✓ Services = orchestration and calculations
✓ Rules = pure decision logic (never called from routes)
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import and_
from modules.organizations.models import Organization
from modules.businesses.models import Business
from modules.statements.models import BusinessStatement
from modules.evidence.models import BusinessEvidence
from modules.auth.models import User, UserOrganizationPermission
from modules.compliance.models import ComplianceAlert, ComplianceProfile, ComplianceSignal
from modules.compliance.services import ComplianceService
from core.extensions import db

compliance_bp = Blueprint('compliance', __name__)
compliance_service = ComplianceService()


# ============================================================================
# RISK INTELLIGENCE ENDPOINTS (Phase-3)
# ============================================================================

@compliance_bp.route('/orgs/<int:org_id>/risk-summary', methods=['GET'])
@jwt_required()
def organization_risk_summary(org_id):
    """
    Get compliance risk summary for organization.
    
    Shows:
    - Risky businesses (low discipline score)
    - GST threshold risks
    - Weak evidence count
    - Open alerts summary
    
    THIS IS PRESENTATION ONLY - all logic in ComplianceService.
    """
    current_user_id = get_jwt_identity()
    
    # Verify user access
    perm = UserOrganizationPermission.query.filter_by(
        user_id=current_user_id,
        org_id=org_id
    ).first()
    
    if not perm:
        return {'error': 'Access denied'}, 403
    
    org = Organization.query.get(org_id)
    if not org:
        return {'error': 'Organization not found'}, 404
    
    # Get all businesses
    businesses = Business.query.filter_by(org_id=org_id).all()
    business_ids = [b.id for b in businesses]
    
    if not business_ids:
        return jsonify({
            'organization_id': org_id,
            'risky_businesses': [],
            'approaching_gst_threshold': [],
            'weak_evidence_businesses': [],
            'open_alerts_summary': {
                'critical': 0, 'high': 0, 'medium': 0, 'low': 0, 'total': 0
            }
        }), 200
    
    # Risky businesses (discipline < 50)
    risky = ComplianceProfile.query.filter(
        and_(
            ComplianceProfile.business_id.in_(business_ids),
            ComplianceProfile.discipline_score < 50
        )
    ).order_by(ComplianceProfile.discipline_score.asc()).all()
    
    risky_data = [
        {
            'business_id': p.business_id,
            'business_name': p.business.name,
            'discipline_score': p.discipline_score,
            'evidence_health': p.evidence_health,
            'estimated_turnover': p.estimated_turnover,
            'gst_risk_level': p.gst_risk_level.value if hasattr(p.gst_risk_level, 'value') else str(p.gst_risk_level)
        }
        for p in risky
    ]
    
    # GST threshold risks (estimated_turnover > 20L)
    gst_risks = ComplianceProfile.query.filter(
        and_(
            ComplianceProfile.business_id.in_(business_ids),
            ComplianceProfile.estimated_turnover > 2_000_000
        )
    ).order_by(ComplianceProfile.estimated_turnover.desc()).all()
    
    gst_data = [
        {
            'business_id': p.business_id,
            'business_name': p.business.name,
            'estimated_turnover': p.estimated_turnover,
            'gst_risk_level': p.gst_risk_level.value if hasattr(p.gst_risk_level, 'value') else str(p.gst_risk_level)
        }
        for p in gst_risks
    ]
    
    # Weak evidence businesses (evidence_health < 50)
    weak_evidence = ComplianceProfile.query.filter(
        and_(
            ComplianceProfile.business_id.in_(business_ids),
            ComplianceProfile.evidence_health < 50
        )
    ).order_by(ComplianceProfile.evidence_health.asc()).all()
    
    weak_data = [
        {
            'business_id': p.business_id,
            'business_name': p.business.name,
            'evidence_health': p.evidence_health,
            'discipline_score': p.discipline_score
        }
        for p in weak_evidence
    ]
    
    # Open alerts summary
    open_alerts = ComplianceAlert.query.filter(
        and_(
            ComplianceAlert.business_id.in_(business_ids),
            ComplianceAlert.status.in_([
                ComplianceAlert.AlertStatus.OPEN,
                ComplianceAlert.AlertStatus.ACKNOWLEDGED
            ])
        )
    ).all()
    
    alert_summary = {
        'critical': sum(1 for a in open_alerts if str(a.severity) == 'critical'),
        'high': sum(1 for a in open_alerts if str(a.severity) == 'high'),
        'medium': sum(1 for a in open_alerts if str(a.severity) == 'medium'),
        'low': sum(1 for a in open_alerts if str(a.severity) == 'low'),
        'total': len(open_alerts)
    }
    
    return jsonify({
        'organization_id': org_id,
        'organization_name': org.name,
        'total_businesses': len(businesses),
        'risky_businesses': {
            'count': len(risky_data),
            'list': risky_data[:10]  # Top 10
        },
        'approaching_gst_threshold': {
            'count': len(gst_data),
            'list': gst_data[:10]
        },
        'weak_evidence_businesses': {
            'count': len(weak_data),
            'list': weak_data[:10]
        },
        'open_alerts_summary': alert_summary
    }), 200


@compliance_bp.route('/businesses/<int:business_id>/profile', methods=['GET'])
@jwt_required()
def business_compliance_profile(business_id):
    """
    Get compliance profile for a business.
    
    Shows:
    - Discipline score
    - Evidence health
    - GST risk level
    - Latest signals
    - Open alerts
    
    THIS IS PRESENTATION ONLY.
    """
    current_user_id = get_jwt_identity()
    
    business = Business.query.get(business_id)
    if not business:
        return {'error': 'Business not found'}, 404
    
    # Verify user access
    perm = UserOrganizationPermission.query.filter_by(
        user_id=current_user_id,
        org_id=business.org_id
    ).first()
    
    if not perm:
        return {'error': 'Access denied'}, 403
    
    # Get profile
    profile = ComplianceProfile.query.filter_by(business_id=business_id).first()
    if not profile:
        return {'error': 'Profile not found. Run evaluation first.'}, 404
    
    # Get latest signal
    signal = ComplianceSignal.query.filter_by(
        business_id=business_id
    ).order_by(ComplianceSignal.signal_date.desc()).first()
    
    # Get open alerts for this business
    open_alerts = ComplianceAlert.query.filter(
        and_(
            ComplianceAlert.business_id == business_id,
            ComplianceAlert.status.in_([
                ComplianceAlert.AlertStatus.OPEN,
                ComplianceAlert.AlertStatus.ACKNOWLEDGED
            ])
        )
    ).order_by(ComplianceAlert.created_at.desc()).all()
    
    alerts_data = [
        {
            'id': a.id,
            'alert_type': a.alert_type.value if hasattr(a.alert_type, 'value') else str(a.alert_type),
            'severity': a.severity.value if hasattr(a.severity, 'value') else str(a.severity),
            'reason': a.reason,
            'rule_triggered': a.rule_that_triggered,
            'status': a.status.value if hasattr(a.status, 'value') else str(a.status),
            'created_at': a.created_at.isoformat()
        }
        for a in open_alerts
    ]
    
    signal_data = None
    if signal:
        signal_data = {
            'signal_date': signal.signal_date.isoformat(),
            'daily_turnover': signal.daily_turnover,
            'monthly_turnover': signal.monthly_turnover,
            'evidence_ratio': round(signal.evidence_ratio * 100, 1),  # As percentage
            'weak_evidence_rate': round(signal.weak_evidence_rate * 100, 1),
            'silence_days': signal.silence_days,
            'abnormal_spike_detected': signal.abnormal_spike_flag
        }
    
    return jsonify({
        'business_id': business_id,
        'business_name': business.name,
        'profile': {
            'discipline_score': profile.discipline_score,
            'evidence_health': profile.evidence_health,
            'estimated_turnover': profile.estimated_turnover,
            'gst_risk_level': profile.gst_risk_level.value if hasattr(profile.gst_risk_level, 'value') else str(profile.gst_risk_level),
            'last_updated': profile.last_updated.isoformat()
        },
        'latest_signal': signal_data,
        'open_alerts': {
            'count': len(alerts_data),
            'alerts': alerts_data
        }
    }), 200


@compliance_bp.route('/orgs/<int:org_id>/alerts/open', methods=['GET'])
@jwt_required()
def organization_open_alerts(org_id):
    """
    Get all open alerts for an organization.
    
    Filterable by:
    - severity (critical, high, medium, low)
    - business_id
    - alert_type
    """
    current_user_id = get_jwt_identity()
    
    # Verify access
    perm = UserOrganizationPermission.query.filter_by(
        user_id=current_user_id,
        org_id=org_id
    ).first()
    
    if not perm:
        return {'error': 'Access denied'}, 403
    
    org = Organization.query.get(org_id)
    if not org:
        return {'error': 'Organization not found'}, 404
    
    # Get all business IDs for this org
    business_ids = [b.id for b in Business.query.filter_by(org_id=org_id).all()]
    
    if not business_ids:
        return jsonify({
            'organization_id': org_id,
            'alerts': [],
            'total': 0
        }), 200
    
    # Get query parameters for filtering
    severity_filter = request.args.get('severity')  # critical, high, medium, low
    business_id_filter = request.args.get('business_id', type=int)
    alert_type_filter = request.args.get('alert_type')
    
    # Base query
    query = ComplianceAlert.query.filter(
        and_(
            ComplianceAlert.business_id.in_(business_ids),
            ComplianceAlert.status.in_([
                ComplianceAlert.AlertStatus.OPEN,
                ComplianceAlert.AlertStatus.ACKNOWLEDGED
            ])
        )
    )
    
    # Apply filters
    if severity_filter:
        query = query.filter(ComplianceAlert.severity == severity_filter)
    if business_id_filter:
        query = query.filter(ComplianceAlert.business_id == business_id_filter)
    if alert_type_filter:
        query = query.filter(ComplianceAlert.alert_type == alert_type_filter)
    
    alerts = query.order_by(ComplianceAlert.created_at.desc()).all()
    
    alerts_data = [
        {
            'id': a.id,
            'business_id': a.business_id,
            'business_name': a.business.name if a.business else 'Unknown',
            'alert_type': a.alert_type.value if hasattr(a.alert_type, 'value') else str(a.alert_type),
            'severity': a.severity.value if hasattr(a.severity, 'value') else str(a.severity),
            'reason': a.reason,
            'rule_triggered': a.rule_that_triggered,
            'status': a.status.value if hasattr(a.status, 'value') else str(a.status),
            'created_at': a.created_at.isoformat()
        }
        for a in alerts
    ]
    
    return jsonify({
        'organization_id': org_id,
        'organization_name': org.name,
        'filters': {
            'severity': severity_filter,
            'business_id': business_id_filter,
            'alert_type': alert_type_filter
        },
        'alerts': alerts_data,
        'total': len(alerts_data)
    }), 200


@compliance_bp.route('/compliance/alerts/<int:alert_id>/acknowledge', methods=['POST'])
@jwt_required()
def acknowledge_alert(alert_id):
    """
    CA acknowledges an alert (marks as seen/reviewed).
    """
    current_user_id = get_jwt_identity()
    
    alert = ComplianceAlert.query.get(alert_id)
    if not alert:
        return {'error': 'Alert not found'}, 404
    
    # Verify user has access to this org
    business = alert.business
    perm = UserOrganizationPermission.query.filter_by(
        user_id=current_user_id,
        org_id=business.org_id
    ).first()
    
    if not perm:
        return {'error': 'Access denied'}, 403
    
    # Mark as acknowledged
    alert.status = ComplianceAlert.AlertStatus.ACKNOWLEDGED
    db.session.commit()
    
    return jsonify({
        'alert_id': alert.id,
        'status': alert.status.value if hasattr(alert.status, 'value') else str(alert.status)
    }), 200


@compliance_bp.route('/compliance/alerts/<int:alert_id>/resolve', methods=['POST'])
@jwt_required()
def resolve_alert(alert_id):
    """
    CA resolves an alert (marks as addressed/handled).
    """
    current_user_id = get_jwt_identity()
    
    alert = ComplianceAlert.query.get(alert_id)
    if not alert:
        return {'error': 'Alert not found'}, 404
    
    # Verify user has access
    business = alert.business
    perm = UserOrganizationPermission.query.filter_by(
        user_id=current_user_id,
        org_id=business.org_id
    ).first()
    
    if not perm:
        return {'error': 'Access denied'}, 403
    
    # Mark as resolved
    from datetime import datetime
    alert.status = ComplianceAlert.AlertStatus.RESOLVED
    alert.resolved_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'alert_id': alert.id,
        'status': alert.status.value if hasattr(alert.status, 'value') else str(alert.status),
        'resolved_at': alert.resolved_at.isoformat()
    }), 200


@compliance_bp.route('/orgs/<int:org_id>/discipline-ranking', methods=['GET'])
@jwt_required()
def organization_discipline_ranking(org_id):
    """
    Get discipline score ranking for all businesses in org.
    
    Shows:
    - Top 10 most compliant businesses
    - Bottom 10 least compliant businesses
    """
    current_user_id = get_jwt_identity()
    
    # Verify access
    perm = UserOrganizationPermission.query.filter_by(
        user_id=current_user_id,
        org_id=org_id
    ).first()
    
    if not perm:
        return {'error': 'Access denied'}, 403
    
    org = Organization.query.get(org_id)
    if not org:
        return {'error': 'Organization not found'}, 404
    
    # Get all businesses
    business_ids = [b.id for b in Business.query.filter_by(org_id=org_id).all()]
    
    if not business_ids:
        return jsonify({
            'organization_id': org_id,
            'top_compliant': [],
            'bottom_compliant': []
        }), 200
    
    # Get all profiles for org
    profiles = ComplianceProfile.query.filter(
        ComplianceProfile.business_id.in_(business_ids)
    ).all()
    
    # Sort by discipline score
    sorted_profiles = sorted(profiles, key=lambda p: p.discipline_score, reverse=True)
    
    profile_data = [
        {
            'business_id': p.business_id,
            'business_name': p.business.name,
            'discipline_score': p.discipline_score,
            'evidence_health': p.evidence_health,
            'estimated_turnover': p.estimated_turnover
        }
        for p in sorted_profiles
    ]
    
    return jsonify({
        'organization_id': org_id,
        'organization_name': org.name,
        'top_compliant': profile_data[:10],  # Top 10
        'bottom_compliant': list(reversed(profile_data[-10:])),  # Bottom 10
        'total_ranked': len(profile_data)
    }), 200


# ============================================================================
# LEGACY ENDPOINTS (Kept for backward compatibility, will be deprecated)
# ============================================================================

@jwt_required()
def organization_dashboard(org_id):
    """
    Get compliance dashboard for an organization.
    Shows all businesses under the org with their compliance status.
    """
    current_user_id = get_jwt_identity()
    
    # Verify user has access to this organization
    perm = UserOrganizationPermission.query.filter_by(
        user_id=current_user_id,
        org_id=org_id
    ).first()
    
    if not perm:
        return {'error': 'Access denied'}, 403
    
    org = Organization.query.get(org_id)
    if not org:
        return {'error': 'Organization not found'}, 404
    
    # Get all businesses for this organization
    businesses = Business.query.filter_by(org_id=org_id).all()
    
    dashboard_data = {
        'organization': {
            'id': org.id,
            'name': org.name,
            'created_at': org.created_at.isoformat()
        },
        'summary': {
            'total_businesses': len(businesses),
            'statements_count': db.session.query(BusinessStatement).filter(
                BusinessStatement.business_id.in_([b.id for b in businesses])
            ).count() if businesses else 0,
            'high_confidence_count': db.session.query(BusinessStatement).filter(
                BusinessStatement.business_id.in_([b.id for b in businesses]),
                BusinessStatement.confidence_level == 'high'
            ).count() if businesses else 0,
            'weak_evidence_count': db.session.query(BusinessEvidence).filter(
                BusinessEvidence.business_id.in_([b.id for b in businesses]),
                BusinessEvidence.evidence_strength == 'weak'
            ).count() if businesses else 0
        },
        'businesses': [
            {
                'id': b.id,
                'name': b.name,
                'whatsapp_phone': b.whatsapp_phone,
                'statements_count': BusinessStatement.query.filter_by(business_id=b.id).count(),
                'evidence_count': BusinessEvidence.query.filter_by(business_id=b.id).count()
            }
            for b in businesses
        ]
    }
    
    return jsonify(dashboard_data), 200


@compliance_bp.route('/businesses/<int:business_id>/statements', methods=['GET'])
@jwt_required()
def business_statements(business_id):
    """
    Get all statements for a business.
    Includes confidence levels and linked evidence.
    """
    current_user_id = get_jwt_identity()
    
    business = Business.query.get(business_id)
    if not business:
        return {'error': 'Business not found'}, 404
    
    # Verify user has access
    perm = UserOrganizationPermission.query.filter_by(
        user_id=current_user_id,
        org_id=business.org_id
    ).first()
    
    if not perm:
        return {'error': 'Access denied'}, 403
    
    statements = BusinessStatement.query.filter_by(business_id=business_id).order_by(
        BusinessStatement.created_at.desc()
    ).all()
    
    statements_data = [
        {
            'id': s.id,
            'amount': s.amount,
            'currency': s.currency,
            'type': s.statement_type,
            'description': s.description,
            'confidence_level': s.confidence_level,
            'transaction_date': s.transaction_date.isoformat() if s.transaction_date else None,
            'created_at': s.created_at.isoformat(),
            'evidence_id': s.whatsapp_message_id
        }
        for s in statements
    ]
    
    return jsonify({
        'business_id': business_id,
        'business_name': business.name,
        'statements': statements_data,
        'total_count': len(statements_data)
    }), 200


@compliance_bp.route('/businesses/<int:business_id>/evidence', methods=['GET'])
@jwt_required()
def business_evidence(business_id):
    """
    Get all evidence for a business.
    Includes OCR results and strength classification.
    """
    current_user_id = get_jwt_identity()
    
    business = Business.query.get(business_id)
    if not business:
        return {'error': 'Business not found'}, 404
    
    # Verify user has access
    perm = UserOrganizationPermission.query.filter_by(
        user_id=current_user_id,
        org_id=business.org_id
    ).first()
    
    if not perm:
        return {'error': 'Access denied'}, 403
    
    evidence_list = BusinessEvidence.query.filter_by(business_id=business_id).order_by(
        BusinessEvidence.created_at.desc()
    ).all()
    
    evidence_data = [
        {
            'id': e.id,
            'file_name': e.file_name,
            'evidence_type': e.evidence_type,
            'strength': e.evidence_strength,
            'quality_score': e.quality_score,
            'status': e.status,
            'detected_amount': e.detected_amount,
            'detected_gstin': e.detected_gstin,
            'detected_date': e.detected_date.isoformat() if e.detected_date else None,
            'ocr_text_preview': e.ocr_text[:100] if e.ocr_text else None,
            'created_at': e.created_at.isoformat()
        }
        for e in evidence_list
    ]
    
    return jsonify({
        'business_id': business_id,
        'business_name': business.name,
        'evidence': evidence_data,
        'total_count': len(evidence_data),
        'strength_breakdown': {
            'strong': sum(1 for e in evidence_list if e.evidence_strength == 'strong'),
            'medium': sum(1 for e in evidence_list if e.evidence_strength == 'medium'),
            'weak': sum(1 for e in evidence_list if e.evidence_strength == 'weak')
        }
    }), 200


@compliance_bp.route('/businesses/<int:business_id>/weak-evidence', methods=['GET'])
@jwt_required()
def weak_evidence(business_id):
    """
    Get weak/problematic evidence that needs review.
    Helps CA prioritize manual verification.
    """
    current_user_id = get_jwt_identity()
    
    business = Business.query.get(business_id)
    if not business:
        return {'error': 'Business not found'}, 404
    
    # Verify user has access
    perm = UserOrganizationPermission.query.filter_by(
        user_id=current_user_id,
        org_id=business.org_id
    ).first()
    
    if not perm:
        return {'error': 'Access denied'}, 403
    
    # Get weak and needs_review evidence
    weak_evidence_list = BusinessEvidence.query.filter_by(
        business_id=business_id
    ).filter(
        db.or_(
            BusinessEvidence.evidence_strength == 'weak',
            BusinessEvidence.status == 'needs_review'
        )
    ).order_by(BusinessEvidence.quality_score.asc()).all()
    
    evidence_data = [
        {
            'id': e.id,
            'file_name': e.file_name,
            'reason': 'low_quality' if e.quality_score < 80 else 'incomplete_ocr',
            'quality_score': e.quality_score,
            'detected_amount': e.detected_amount,
            'detected_gstin': e.detected_gstin,
            'status': e.status,
            'created_at': e.created_at.isoformat()
        }
        for e in weak_evidence_list
    ]
    
    return jsonify({
        'business_id': business_id,
        'business_name': business.name,
        'weak_evidence': evidence_data,
        'total_count': len(evidence_data),
        'recommended_actions': [
            'Request better quality photos',
            'Request additional documents',
            'Manually verify the transactions'
        ] if len(evidence_data) > 0 else []
    }), 200


@compliance_bp.route('/orgs/<int:org_id>/summary', methods=['GET'])
@jwt_required()
def organization_summary(org_id):
    """
    Get comprehensive compliance summary for an organization.
    """
    current_user_id = get_jwt_identity()
    
    perm = UserOrganizationPermission.query.filter_by(
        user_id=current_user_id,
        org_id=org_id
    ).first()
    
    if not perm:
        return {'error': 'Access denied'}, 403
    
    org = Organization.query.get(org_id)
    if not org:
        return {'error': 'Organization not found'}, 404
    
    businesses = Business.query.filter_by(org_id=org_id).all()
    business_ids = [b.id for b in businesses]
    
    statements = BusinessStatement.query.filter(
        BusinessStatement.business_id.in_(business_ids)
    ).all() if business_ids else []
    
    evidence_list = BusinessEvidence.query.filter(
        BusinessEvidence.business_id.in_(business_ids)
    ).all() if business_ids else []
    
    summary = {
        'organization': {
            'id': org.id,
            'name': org.name
        },
        'statistics': {
            'businesses': len(businesses),
            'total_statements': len(statements),
            'total_evidence': len(evidence_list),
            'confidence_breakdown': {
                'high': sum(1 for s in statements if s.confidence_level == 'high'),
                'medium': sum(1 for s in statements if s.confidence_level == 'medium'),
                'low': sum(1 for s in statements if s.confidence_level == 'low')
            },
            'evidence_strength': {
                'strong': sum(1 for e in evidence_list if e.evidence_strength == 'strong'),
                'medium': sum(1 for e in evidence_list if e.evidence_strength == 'medium'),
                'weak': sum(1 for e in evidence_list if e.evidence_strength == 'weak')
            }
        },
        'compliance_status': 'good' if sum(1 for s in statements if s.confidence_level == 'high') > len(statements) * 0.7 else 'needs_review'
    }
    
    return jsonify(summary), 200
