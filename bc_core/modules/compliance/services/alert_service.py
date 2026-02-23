"""
Alert Service

Manages compliance alerts lifecycle.

Architecture:
- _create_alert(): Internal only, called by rule engine
- query_open_alerts(): Get active alerts
- resolve_alert(): Mark as resolved by CA
- get_alert_summary(): Count by severity

CRITICAL: Only rule engine calls _create_alert().
Routes must never directly create alerts.
"""

from datetime import datetime
from typing import List, Dict, Optional
from sqlalchemy import and_
from core.extensions import db
from modules.compliance.models import ComplianceAlert


class AlertService:
    """
    Alert management service.
    
    Responsible for:
    - Creating alerts (internal only, from rule engine)
    - Querying alert state
    - Resolving alerts (marking as handled by CA)
    - Deduplicating alerts (prevent duplicates same day)
    """
    
    def _create_alert(
        self,
        business_id: int,
        alert_type: str,
        severity: str,
        reason: str,
        rule_that_triggered: str
    ) -> ComplianceAlert:
        """
        Create a compliance alert.
        
        INTERNAL ONLY - Called only by RuleEngine.
        Routes must never call this directly.
        
        Deduplicates: Prevents creating duplicate alerts for same rule, same day.
        
        Args:
            business_id: Business that triggered alert
            alert_type: 'threshold', 'data_quality', 'behavior', 'audit_readiness'
            severity: 'critical', 'high', 'medium', 'low'
            reason: Human-readable reason text
            rule_that_triggered: Name of rule that created alert
        
        Returns:
            ComplianceAlert instance (new or existing if duplicate)
        """
        # Check for existing open alert from same rule today
        today = datetime.utcnow().date()
        
        existing_alert = ComplianceAlert.query.filter(
            and_(
                ComplianceAlert.business_id == business_id,
                ComplianceAlert.rule_that_triggered == rule_that_triggered,
                ComplianceAlert.status.in_([
                    ComplianceAlert.AlertStatus.OPEN,
                    ComplianceAlert.AlertStatus.ACKNOWLEDGED
                ]),
                db.func.date(ComplianceAlert.created_at) == today
            )
        ).first()
        
        if existing_alert:
            # Duplicate alert - return existing
            return existing_alert
        
        # Create new alert
        alert = ComplianceAlert(
            business_id=business_id,
            alert_type=alert_type,
            severity=severity,
            reason=reason,
            rule_that_triggered=rule_that_triggered,
            status=ComplianceAlert.AlertStatus.OPEN,
            created_at=datetime.utcnow()
        )
        
        db.session.add(alert)
        db.session.commit()
        
        return alert
    
    def query_open_alerts(self, business_id: Optional[int] = None) -> List[ComplianceAlert]:
        """
        Query open alerts (status = OPEN or ACKNOWLEDGED).
        
        Args:
            business_id: Filter by business (None = all)
        
        Returns:
            List of ComplianceAlert instances
        """
        query = ComplianceAlert.query.filter(
            ComplianceAlert.status.in_([
                ComplianceAlert.AlertStatus.OPEN,
                ComplianceAlert.AlertStatus.ACKNOWLEDGED
            ])
        )
        
        if business_id:
            query = query.filter(ComplianceAlert.business_id == business_id)
        
        return query.order_by(ComplianceAlert.created_at.desc()).all()
    
    def acknowledge_alert(self, alert_id: int) -> ComplianceAlert:
        """
        Mark alert as acknowledged by CA.
        
        Args:
            alert_id: Alert ID
        
        Returns:
            Updated ComplianceAlert
        """
        alert = ComplianceAlert.query.get(alert_id)
        if not alert:
            raise ValueError(f"Alert {alert_id} not found")
        
        alert.status = ComplianceAlert.AlertStatus.ACKNOWLEDGED
        db.session.commit()
        
        return alert
    
    def resolve_alert(self, alert_id: int) -> ComplianceAlert:
        """
        Mark alert as resolved by CA.
        
        Args:
            alert_id: Alert ID
        
        Returns:
            Updated ComplianceAlert
        """
        alert = ComplianceAlert.query.get(alert_id)
        if not alert:
            raise ValueError(f"Alert {alert_id} not found")
        
        alert.status = ComplianceAlert.AlertStatus.RESOLVED
        alert.resolved_at = datetime.utcnow()
        db.session.commit()
        
        return alert
    
    def get_alert_summary(self, business_id: Optional[int] = None) -> Dict[str, int]:
        """
        Get count of open alerts by severity.
        
        Args:
            business_id: Filter by business (None = all)
        
        Returns:
            Dict with keys: 'critical', 'high', 'medium', 'low'
        """
        summary = {
            'critical': 0,
            'high': 0,
            'medium': 0,
            'low': 0,
            'total': 0,
        }
        
        query = ComplianceAlert.query.filter(
            ComplianceAlert.status.in_([
                ComplianceAlert.AlertStatus.OPEN,
                ComplianceAlert.AlertStatus.ACKNOWLEDGED
            ])
        )
        
        if business_id:
            query = query.filter(ComplianceAlert.business_id == business_id)
        
        alerts = query.all()
        
        for alert in alerts:
            severity = alert.severity.value if hasattr(alert.severity, 'value') else str(alert.severity)
            summary[severity] = summary.get(severity, 0) + 1
            summary['total'] += 1
        
        return summary
