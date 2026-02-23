"""
Compliance Service Orchestrator

Main orchestration service that ties together:
1. Signal calculation
2. Rule evaluation
3. Alert creation
4. Profile update

This is the "brain" of Phase-3:
Signal Calculation → Rule Evaluation → Alert Creation → Profile Update
"""

from typing import Tuple, List
from datetime import datetime
from modules.compliance.services.signal_service import ComplianceSignalService
from modules.compliance.services.profile_calculator import ProfileCalculator
from modules.compliance.services.alert_service import AlertService
from modules.compliance.rules import RuleEngine
from modules.compliance.rules.threshold_rules import (
    TurnoverThresholdRule,
    GSTThresholdRule,
    EvidenceBelowThresholdRule,
    ProlongedSilenceRule,
)
from modules.compliance.rules.data_quality_rules import (
    WeakEvidenceRule,
    UnverifiedAmountsRule,
    LowConfidenceRule,
)
from modules.compliance.rules.behavior_rules import (
    AbnormalActivityRule,
    LowDisciplineRule,
    AuditReadinessRule,
)
from modules.compliance.models import ComplianceSignal, ComplianceAlert, ComplianceProfile


class ComplianceService:
    """
    Main compliance service orchestrator.
    
    Executes the complete compliance pipeline:
    1. Calculate signals from raw data
    2. Evaluate rules against signals
    3. Create alerts for violations
    4. Update profile with aggregated scores
    
    Usage:
        service = ComplianceService()
        signal, alerts, profile = service.evaluate_business(business_id)
    """
    
    def __init__(self):
        """Initialize service with rule engine and all rules."""
        self.signal_service = ComplianceSignalService()
        self.alert_service = AlertService()
        self.profile_calculator = ProfileCalculator()
        
        # Initialize rule engine with all rules
        self.rule_engine = RuleEngine()
        self._register_all_rules()
    
    def _register_all_rules(self) -> None:
        """Register all compliance rules with the engine."""
        # Threshold rules
        self.rule_engine.register_rule(TurnoverThresholdRule())
        self.rule_engine.register_rule(GSTThresholdRule())
        self.rule_engine.register_rule(EvidenceBelowThresholdRule())
        self.rule_engine.register_rule(ProlongedSilenceRule())
        
        # Data quality rules
        self.rule_engine.register_rule(WeakEvidenceRule())
        self.rule_engine.register_rule(UnverifiedAmountsRule())
        self.rule_engine.register_rule(LowConfidenceRule())
        
        # Behavior rules
        self.rule_engine.register_rule(AbnormalActivityRule())
        self.rule_engine.register_rule(LowDisciplineRule())
        self.rule_engine.register_rule(AuditReadinessRule())
    
    def evaluate_business(
        self,
        business_id: int,
        eval_date: datetime = None
    ) -> Tuple[ComplianceSignal, List[ComplianceAlert], ComplianceProfile]:
        """
        Execute complete compliance evaluation for a business.
        
        Pipeline:
        1. Signal Calculation (pure calculations from raw data)
        2. Rule Evaluation (check signals against policies)
        3. Alert Creation (create for rule violations)
        4. Profile Update (aggregate scores)
        
        Args:
            business_id: Business to evaluate
            eval_date: Date to evaluate (defaults to today)
        
        Returns:
            Tuple of (signal, alerts, profile)
        """
        if eval_date is None:
            eval_date = datetime.utcnow()
        
        # Step 1: Calculate signals
        signal_dict = ComplianceSignalService.get_business_signals(business_id, eval_date)
        signal = ComplianceSignalService.store_signal(signal_dict)
        
        # Step 2: Evaluate rules against signal
        created_alerts = self.rule_engine.run(business_id, signal)
        
        # Step 3: Update profile (uses signals + alerts)
        profile = ProfileCalculator.update_profile(business_id)
        
        return signal, created_alerts, profile
    
    def evaluate_all_businesses(self) -> dict:
        """
        Evaluate all businesses in system.
        
        Used for daily compliance batch job.
        
        Returns:
            Dict with:
            - 'total': number of businesses evaluated
            - 'signals_created': count of new signals
            - 'alerts_created': count of new alerts
            - 'profiles_updated': count of updated profiles
            - 'errors': list of businesses that failed
        """
        from modules.businesses.models import Business
        
        result = {
            'total': 0,
            'signals_created': 0,
            'alerts_created': 0,
            'profiles_updated': 0,
            'errors': [],
        }
        
        # Get all active businesses
        businesses = Business.query.all()
        
        for business in businesses:
            try:
                signal, alerts, profile = self.evaluate_business(business.id)
                result['total'] += 1
                result['signals_created'] += 1
                result['alerts_created'] += len(alerts)
                result['profiles_updated'] += 1
            except Exception as e:
                result['errors'].append({
                    'business_id': business.id,
                    'business_name': business.name,
                    'error': str(e)
                })
        
        return result
    
    def get_business_risk_profile(self, business_id: int) -> dict:
        """
        Get complete risk profile for a business.
        
        Aggregates: signal, profile, alerts, recommendations.
        
        Args:
            business_id: Business ID
        
        Returns:
            Dict with risk assessment
        """
        # Get latest signal
        signal = ComplianceSignal.query.filter_by(
            business_id=business_id
        ).order_by(ComplianceSignal.signal_date.desc()).first()
        
        # Get profile
        profile = ComplianceProfile.query.filter_by(business_id=business_id).first()
        
        # Get open alerts
        open_alerts = self.alert_service.query_open_alerts(business_id)
        
        return {
            'business_id': business_id,
            'signal': signal,
            'profile': profile,
            'open_alerts': open_alerts,
            'alert_summary': self.alert_service.get_alert_summary(business_id),
        }
