"""
Data Quality Rules

Rules that trigger on poor evidence/statement quality.

Types:
- WeakEvidenceRule: Too many documents marked as weak quality
- UnverifiedAmountsRule: Statements without verified amounts  
- LowConfidenceRule: Parsed amounts have low OCR confidence
"""

from typing import Optional, Dict
from sqlalchemy import and_, func
from modules.compliance.rules.base import BaseRule
from modules.compliance.models import ComplianceSignal
from modules.statements.models import BusinessStatement
from modules.evidence.models import BusinessEvidence
from core.extensions import db


class WeakEvidenceRule(BaseRule):
    """
    Alert when too many documents are marked as weak quality.
    
    Detects: Poor evidence collection, fraudulent documents, OCR failures.
    
    Threshold: Weak evidence rate > 40%
    """
    
    def __init__(self):
        super().__init__("WeakEvidence")
    
    def evaluate(self, business_id: int, signal: ComplianceSignal) -> Optional[Dict[str, str]]:
        """
        Check if weak evidence percentage exceeds threshold.
        
        Args:
            business_id: Business ID
            signal: ComplianceSignal with weak_evidence_rate
        
        Returns:
            Alert reason if triggered, None otherwise
        """
        WEAK_EVIDENCE_THRESHOLD = 0.40  # 40%
        
        if signal.weak_evidence_rate > WEAK_EVIDENCE_THRESHOLD:
            percent = signal.weak_evidence_rate * 100
            return {
                'reason': f'{percent:.0f}% of evidence documents marked as weak quality (threshold: 40%)'
            }
        
        return None
    
    def get_severity(self) -> str:
        return 'medium'
    
    def get_type(self) -> str:
        return 'data_quality'


class UnverifiedAmountsRule(BaseRule):
    """
    Alert when statements have unverified/unparsed amounts.
    
    Detects: Poor OCR, corrupted documents, unreadable statements.
    
    Threshold: < 60% of statements have detected amounts
    """
    
    def __init__(self):
        super().__init__("UnverifiedAmounts")
    
    def evaluate(self, business_id: int, signal: ComplianceSignal) -> Optional[Dict[str, str]]:
        """
        Check if too many statement amounts are unverified.
        
        Args:
            business_id: Business ID
            signal: ComplianceSignal
        
        Returns:
            Alert reason if triggered, None otherwise
        """
        # Total statements
        total_statements = db.session.query(
            func.count(BusinessStatement.id)
        ).filter(
            BusinessStatement.business_id == business_id
        ).scalar() or 0
        
        if total_statements == 0:
            return None  # No data to verify
        
        # Statements with verified amounts (has detected amount in evidence)
        verified_statements = db.session.query(
            func.count(func.distinct(BusinessStatement.id))
        ).select_from(BusinessStatement).join(
            BusinessEvidence,
            BusinessStatement.id == BusinessEvidence.business_statement_id,
            isouter=False
        ).filter(
            and_(
                BusinessStatement.business_id == business_id,
                BusinessEvidence.detected_amount.isnot(None)
            )
        ).scalar() or 0
        
        verification_rate = float(verified_statements) / float(total_statements)
        VERIFICATION_THRESHOLD = 0.60  # 60%
        
        if verification_rate < VERIFICATION_THRESHOLD:
            percent = verification_rate * 100
            return {
                'reason': f'Only {percent:.0f}% of statements have verified amounts (threshold: 60%)'
            }
        
        return None
    
    def get_severity(self) -> str:
        return 'medium'
    
    def get_type(self) -> str:
        return 'data_quality'


class LowConfidenceRule(BaseRule):
    """
    Alert when parsed statement amounts have low OCR confidence.
    
    Detects: Poor OCR quality, unreliable amount extraction.
    
    Threshold: < 70% of statements have high OCR confidence
    """
    
    def __init__(self):
        super().__init__("LowConfidence")
    
    def evaluate(self, business_id: int, signal: ComplianceSignal) -> Optional[Dict[str, str]]:
        """
        Check if statement parsing confidence is too low.
        
        Args:
            business_id: Business ID
            signal: ComplianceSignal
        
        Returns:
            Alert reason if triggered, None otherwise
        """
        # Total statements
        total_statements = db.session.query(
            func.count(BusinessStatement.id)
        ).filter(
            BusinessStatement.business_id == business_id
        ).scalar() or 0
        
        if total_statements == 0:
            return None
        
        # High-confidence statements
        high_confidence = db.session.query(
            func.count(BusinessStatement.id)
        ).filter(
            and_(
                BusinessStatement.business_id == business_id,
                BusinessStatement.confidence_level == 'high'
            )
        ).scalar() or 0
        
        confidence_rate = float(high_confidence) / float(total_statements)
        CONFIDENCE_THRESHOLD = 0.70  # 70%
        
        if confidence_rate < CONFIDENCE_THRESHOLD:
            percent = confidence_rate * 100
            return {
                'reason': f'Only {percent:.0f}% of statements parsed with high confidence (threshold: 70%)'
            }
        
        return None
    
    def get_severity(self) -> str:
        return 'low'
    
    def get_type(self) -> str:
        return 'data_quality'
