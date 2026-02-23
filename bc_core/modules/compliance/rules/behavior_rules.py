"""
Behavior & Audit Readiness Rules

Rules based on business behavior patterns and audit preparation.

Types:
- AbnormalActivityRule: Sales spikes detected
- LowDisciplineRule: Discipline score below threshold
- AuditReadinessRule: Business not ready for audit
"""

from typing import Optional, Dict
from modules.compliance.rules.base import BaseRule
from modules.compliance.models import ComplianceSignal, ComplianceProfile
from modules.businesses.models import Business


class AbnormalActivityRule(BaseRule):
    """
    Alert when abnormal sales spike detected.
    
    Detects: Possible fraud, cooking books, hidden activity.
    
    Trigger: Sales > 2.5x monthly average
    """
    
    def __init__(self):
        super().__init__("AbnormalActivity")
    
    def evaluate(self, business_id: int, signal: ComplianceSignal) -> Optional[Dict[str, str]]:
        """
        Check if abnormal sales spike is detected.
        
        Args:
            business_id: Business ID
            signal: ComplianceSignal with abnormal_spike_flag
        
        Returns:
            Alert reason if triggered, None otherwise
        """
        if signal.abnormal_spike_flag:
            return {
                'reason': f'Abnormal sales spike detected (₹{signal.daily_turnover:,.0f} vs monthly average)'
            }
        
        return None
    
    def get_severity(self) -> str:
        return 'high'
    
    def get_type(self) -> str:
        return 'behavior'


class LowDisciplineRule(BaseRule):
    """
    Alert when business shows low compliance discipline.
    
    Detects: Systemically poor compliance (combines multiple factors).
    
    Threshold: Discipline score < 40
    """
    
    def __init__(self):
        super().__init__("LowDiscipline")
    
    def evaluate(self, business_id: int, signal: ComplianceSignal) -> Optional[Dict[str, str]]:
        """
        Check if discipline score is too low.
        
        Args:
            business_id: Business ID
            signal: ComplianceSignal
        
        Returns:
            Alert reason if triggered, None otherwise
        """
        # Get profile (contains discipline_score)
        profile = ComplianceProfile.query.filter_by(business_id=business_id).first()
        if not profile:
            return None  # No profile yet
        
        DISCIPLINE_THRESHOLD = 40  # Score 0-100
        
        if profile.discipline_score < DISCIPLINE_THRESHOLD:
            return {
                'reason': f'Discipline score {profile.discipline_score}/100 indicates systemic compliance issues'
            }
        
        return None
    
    def get_severity(self) -> str:
        return 'critical'
    
    def get_type(self) -> str:
        return 'behavior'


class AuditReadinessRule(BaseRule):
    """
    Alert when business is not prepared for tax audit.
    
    Detects: Insufficient evidence, poor documentation.
    
    Threshold: Evidence health < 50
    """
    
    def __init__(self):
        super().__init__("AuditReadiness")
    
    def evaluate(self, business_id: int, signal: ComplianceSignal) -> Optional[Dict[str, str]]:
        """
        Check if business has adequate evidence for audit.
        
        Args:
            business_id: Business ID
            signal: ComplianceSignal
        
        Returns:
            Alert reason if triggered, None otherwise
        """
        # Get profile (contains evidence_health)
        profile = ComplianceProfile.query.filter_by(business_id=business_id).first()
        if not profile:
            return None  # No profile yet
        
        EVIDENCE_HEALTH_THRESHOLD = 50  # Score 0-100
        
        if profile.evidence_health < EVIDENCE_HEALTH_THRESHOLD:
            return {
                'reason': f'Evidence health {profile.evidence_health}/100 - business not audit-ready'
            }
        
        return None
    
    def get_severity(self) -> str:
        return 'high'
    
    def get_type(self) -> str:
        return 'audit_readiness'
