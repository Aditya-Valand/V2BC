"""
Threshold-Based Compliance Rules

Rules that trigger when financial or reporting thresholds are exceeded.

Types:
- TurnoverThresholdRule: Sales exceed expected amount
- GSTThresholdRule: Estimated turnover crosses GST filing threshold  
- EvidenceBelowThresholdRule: Insufficient document backing
- ProlongedSilenceRule: Business hasn't reported in 30+ days
"""

from typing import Optional, Dict
from modules.compliance.rules.base import BaseRule
from modules.compliance.models import ComplianceSignal
from modules.businesses.models import Business


class TurnoverThresholdRule(BaseRule):
    """
    Alert when monthly turnover significantly exceeds expected.
    
    Detects: Abnormal business activity, possible fraud, cooking.
    
    Threshold: Monthly > Expected * 1.5
    """
    
    def __init__(self):
        super().__init__("TurnoverThreshold")
    
    def evaluate(self, business_id: int, signal: ComplianceSignal) -> Optional[Dict[str, str]]:
        """
        Check if monthly turnover exceeds threshold.
        
        Args:
            business_id: Business ID
            signal: ComplianceSignal with monthly_turnover
        
        Returns:
            Alert reason if triggered, None otherwise
        """
        # Get business expected turnover
        business = Business.query.get(business_id)
        if not business or not business.expected_turnover:
            return None  # Can't evaluate without baseline
        
        # Calculate threshold
        threshold = business.expected_turnover * 1.5
        
        if signal.monthly_turnover > threshold:
            return {
                'reason': f'Monthly turnover ₹{signal.monthly_turnover:,.0f} exceeds expected ₹{business.expected_turnover:,.0f} by 50%'
            }
        
        return None
    
    def get_severity(self) -> str:
        return 'high'
    
    def get_type(self) -> str:
        return 'threshold'


class GSTThresholdRule(BaseRule):
    """
    Alert when business crosses GST filing threshold.
    
    Detects: Businesses entering higher compliance bracket.
    
    Threshold: Estimated turnover > ₹40L
    """
    
    def __init__(self):
        super().__init__("GSTThreshold")
    
    def evaluate(self, business_id: int, signal: ComplianceSignal) -> Optional[Dict[str, str]]:
        """
        Check if business estimated turnover exceeds GST threshold.
        
        Args:
            business_id: Business ID
            signal: ComplianceSignal
        
        Returns:
            Alert reason if triggered, None otherwise
        """
        business = Business.query.get(business_id)
        if not business or not business.expected_turnover:
            return None
        
        GST_HIGH_THRESHOLD = 4_000_000  # ₹40L
        
        if business.expected_turnover > GST_HIGH_THRESHOLD:
            return {
                'reason': f'Estimated turnover ₹{business.expected_turnover:,.0f} exceeds GST filing threshold of ₹40L'
            }
        
        return None
    
    def get_severity(self) -> str:
        return 'high'
    
    def get_type(self) -> str:
        return 'threshold'


class EvidenceBelowThresholdRule(BaseRule):
    """
    Alert when statements lack supporting documentation.
    
    Detects: Insufficient evidence for audit defense.
    
    Threshold: Evidence ratio < 0.5 (< 50% of statements backed)
    """
    
    def __init__(self):
        super().__init__("EvidenceBelowThreshold")
    
    def evaluate(self, business_id: int, signal: ComplianceSignal) -> Optional[Dict[str, str]]:
        """
        Check if evidence backing is below minimum threshold.
        
        Args:
            business_id: Business ID
            signal: ComplianceSignal with evidence_ratio
        
        Returns:
            Alert reason if triggered, None otherwise
        """
        EVIDENCE_MIN_THRESHOLD = 0.5  # 50%
        
        if signal.evidence_ratio < EVIDENCE_MIN_THRESHOLD:
            percent = signal.evidence_ratio * 100
            return {
                'reason': f'Only {percent:.0f}% of statements have supporting documentation (minimum: 50%)'
            }
        
        return None
    
    def get_severity(self) -> str:
        return 'high'
    
    def get_type(self) -> str:
        return 'threshold'


class ProlongedSilenceRule(BaseRule):
    """
    Alert when business hasn't submitted statement for 30+ days.
    
    Detects: Inactive business, reporting failure, possible closure.
    
    Threshold: silence_days > 30
    """
    
    def __init__(self):
        super().__init__("ProlongedSilence")
    
    def evaluate(self, business_id: int, signal: ComplianceSignal) -> Optional[Dict[str, str]]:
        """
        Check if business has gone silent for extended period.
        
        Args:
            business_id: Business ID
            signal: ComplianceSignal with silence_days
        
        Returns:
            Alert reason if triggered, None otherwise
        """
        SILENCE_THRESHOLD = 30  # days
        
        if signal.silence_days > SILENCE_THRESHOLD:
            return {
                'reason': f'No statement submitted for {signal.silence_days} days (threshold: {SILENCE_THRESHOLD} days)'
            }
        
        return None
    
    def get_severity(self) -> str:
        return 'medium'
    
    def get_type(self) -> str:
        return 'behavior'
