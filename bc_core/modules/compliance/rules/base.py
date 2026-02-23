"""
Rule Engine Base Classes

Provides abstract Rule class and RuleEngine executor.

Architecture:
- BaseRule: Abstract rule class (extend this)
- RuleEngine: Executes all rules, creates alerts
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict
from datetime import datetime
from modules.compliance.models import ComplianceAlert, ComplianceSignal
from modules.compliance.services.alert_service import AlertService


class BaseRule(ABC):
    """
    Abstract base for compliance rules.
    
    Each rule evaluates a signal and determines if it violates a policy.
    Rules are:
    - Isolated (independent, no shared state)
    - Testable (pure logic, no side effects)
    - Declarative (express policy intent clearly)
    
    Subclasses must implement: evaluate(), get_severity(), get_type()
    """
    
    def __init__(self, name: str):
        """
        Initialize rule.
        
        Args:
            name: Human-readable rule name (e.g., "TurnoverThreshold")
        """
        self.name = name
    
    @abstractmethod
    def evaluate(self, business_id: int, signal: ComplianceSignal) -> Optional[Dict[str, str]]:
        """
        Evaluate rule against business signal.
        
        Pure function: same input → same output, no side effects.
        
        Args:
            business_id: Business ID being evaluated
            signal: ComplianceSignal with metrics
        
        Returns:
            None if rule passes (no violation)
            Dict with keys 'reason' (string) if rule fails (violation detected)
        
        Example:
            >>> result = rule.evaluate(123, signal)
            >>> if result:
            ...     print(f"Alert: {result['reason']}")
        """
        pass
    
    @abstractmethod
    def get_severity(self) -> str:
        """
        Get alert severity if this rule triggers.
        
        Returns:
            'critical', 'high', 'medium', or 'low'
        """
        pass
    
    @abstractmethod
    def get_type(self) -> str:
        """
        Get alert type for this rule.
        
        Returns:
            'threshold', 'data_quality', 'behavior', or 'audit_readiness'
        """
        pass
    
    def __repr__(self):
        return f'<{self.__class__.__name__} "{self.name}">'


class RuleEngine:
    """
    Compliance rule engine.
    
    Executes registered rules against business signals.
    Creates alerts when rules trigger.
    
    Responsibilities:
    - Register rules
    - Execute all rules for a business
    - Create alerts (only place that creates alerts)
    - Prevent duplicate alerts
    """
    
    def __init__(self):
        """Initialize empty rule registry."""
        self.rules: List[BaseRule] = []
        self.alert_service = AlertService()
    
    def register_rule(self, rule: BaseRule) -> 'RuleEngine':
        """
        Register a rule for execution.
        
        Args:
            rule: Rule instance (extends BaseRule)
        
        Returns:
            Self (for chaining)
        """
        if not isinstance(rule, BaseRule):
            raise TypeError(f"Rule must extend BaseRule, got {type(rule)}")
        self.rules.append(rule)
        return self
    
    def register_rules(self, rules: List[BaseRule]) -> 'RuleEngine':
        """
        Register multiple rules at once.
        
        Args:
            rules: List of Rule instances
        
        Returns:
            Self (for chaining)
        """
        for rule in rules:
            self.register_rule(rule)
        return self
    
    def run(self, business_id: int, signal: ComplianceSignal) -> List[ComplianceAlert]:
        """
        Execute all rules for a business.
        
        Evaluates each rule against the signal.
        Creates alerts for any triggered rules.
        
        Args:
            business_id: Business ID to evaluate
            signal: ComplianceSignal with metrics
        
        Returns:
            List of created ComplianceAlert instances
        """
        created_alerts = []
        
        for rule in self.rules:
            try:
                # Evaluate rule (pure function, no side effects)
                result = rule.evaluate(business_id, signal)
                
                if result:
                    # Rule triggered - create alert
                    alert = self.alert_service._create_alert(
                        business_id=business_id,
                        alert_type=rule.get_type(),
                        severity=rule.get_severity(),
                        reason=result['reason'],
                        rule_that_triggered=rule.name
                    )
                    created_alerts.append(alert)
            
            except Exception as e:
                # Log error but don't stop rule execution
                print(f"Error evaluating rule {rule.name} for business {business_id}: {e}")
                continue
        
        return created_alerts
    
    def run_all_rules(self, business_id: int) -> List[ComplianceAlert]:
        """
        Execute all rules for a business using its latest signal.
        
        Convenience method that fetches latest signal and executes all rules.
        
        Args:
            business_id: Business ID to evaluate
        
        Returns:
            List of created ComplianceAlert instances
        """
        # Get latest signal
        signal = ComplianceSignal.query.filter_by(
            business_id=business_id
        ).order_by(ComplianceSignal.signal_date.desc()).first()
        
        if signal is None:
            # No signal yet - can't evaluate rules
            return []
        
        return self.run(business_id, signal)
