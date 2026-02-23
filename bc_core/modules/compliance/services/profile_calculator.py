"""
Profile Calculator Service

Computes aggregated compliance profiles from signals.

Profile combines:
- Discipline Score: 0-100 (compliance consistency)
- Evidence Health: 0-100 (evidence quality)
- GST Risk Level: low/medium/high (filing threshold classification)
"""

from datetime import datetime
from typing import Dict, Tuple
from sqlalchemy import and_, func
from core.extensions import db
from modules.businesses.models import Business
from modules.compliance.models import (
    ComplianceSignal, ComplianceProfile, ComplianceAlert
)


class ProfileCalculator:
    """
    Computes compliance profiles from signals and alerts.
    
    All calculations are pure functions:
    - Same signal inputs → Same score outputs
    - Deterministic, no randomness
    - No side effects except profile creation
    """
    
    # Scoring weights (must sum to 100)
    TURNOVER_CONSISTENCY_WEIGHT = 25      # % from turnover stability
    EVIDENCE_RATIO_WEIGHT = 30            # % from evidence backing
    SILENCE_PENALTY_WEIGHT = 20           # % from statement recency
    ABNORMAL_ACTIVITY_WEIGHT = 15         # % from absence of spikes
    ALERT_PENALTY_WEIGHT = 10             # % from open alerts
    
    # GST threshold classifications (₹)
    GST_FILING_LOW_LIMIT = 2_000_000      # < 20L: LOW risk
    GST_FILING_HIGH_LIMIT = 4_000_000     # > 40L: HIGH risk
    
    @staticmethod
    def compute_discipline_score(
        business_id: int,
        latest_signals: ComplianceSignal = None,
        open_alerts_count: int = None
    ) -> int:
        """
        Compute discipline score (0-100).
        
        Measures how consistently compliant the business is.
        
        Factors:
        - Turnover consistency (no large gaps)
        - Evidence ratio (statements backed by docs)
        - Statement recency (no long silences)
        - Activity patterns (no abnormal spikes)
        - Open alerts (penalties for violations)
        
        Args:
            business_id: Business ID
            latest_signals: Latest ComplianceSignal (fetched if None)
            open_alerts_count: Number of open alerts (queried if None)
        
        Returns:
            Score 0-100 (higher = more disciplined)
        """
        score = 100  # Start at max
        
        # Fetch latest signal if not provided
        if latest_signals is None:
            latest_signals = ComplianceSignal.query.filter_by(
                business_id=business_id
            ).order_by(ComplianceSignal.signal_date.desc()).first()
        
        if latest_signals is None:
            # No signals yet - neutral score
            return 50
        
        # Fetch open alert count if not provided
        if open_alerts_count is None:
            open_alerts_count = db.session.query(func.count(ComplianceAlert.id)).filter(
                and_(
                    ComplianceAlert.business_id == business_id,
                    ComplianceAlert.status == ComplianceAlert.AlertStatus.OPEN
                )
            ).scalar() or 0
        
        # Factor 1: Turnover consistency (no gaps in daily reporting)
        # If 0 daily turnover, assume closed that day (OK)
        # If many zeros, assume not reporting (BAD)
        if latest_signals.daily_turnover == 0 and latest_signals.silence_days > 7:
            score -= 25  # Max penalty for turnover consistency
        elif latest_signals.daily_turnover == 0:
            score -= 5   # Minor penalty for one-day gap
        # If daily_turnover > 0, no penalty
        
        # Factor 2: Evidence backing ratio (documents for statements)
        # Lower evidence_ratio = lower score
        evidence_penalty = (1.0 - latest_signals.evidence_ratio) * 30
        score -= evidence_penalty
        
        # Factor 3: Silence penalty (days since last statement)
        # 0-7 days: no penalty
        # 7-30 days: gradual penalty
        # 30+ days: max penalty
        if latest_signals.silence_days > 30:
            score -= 20
        elif latest_signals.silence_days > 7:
            score -= (latest_signals.silence_days - 7) * 0.8
        
        # Factor 4: Abnormal activity (spikes indicate possible fraud/cooking)
        if latest_signals.abnormal_spike_flag:
            score -= 15
        
        # Factor 5: Open alerts (each alert reduces score)
        # Critical: -15, High: -10, Medium: -5, Low: -2
        for alert in ComplianceAlert.query.filter_by(
            business_id=business_id,
            status=ComplianceAlert.AlertStatus.OPEN
        ).all():
            if alert.severity == ComplianceAlert.AlertSeverity.CRITICAL:
                score -= 15
            elif alert.severity == ComplianceAlert.AlertSeverity.HIGH:
                score -= 10
            elif alert.severity == ComplianceAlert.AlertSeverity.MEDIUM:
                score -= 5
            elif alert.severity == ComplianceAlert.AlertSeverity.LOW:
                score -= 2
        
        # Clamp score to 0-100
        return max(0, min(100, int(score)))
    
    @staticmethod
    def compute_evidence_health(
        latest_signals: ComplianceSignal = None,
        business_id: int = None
    ) -> int:
        """
        Compute evidence health score (0-100).
        
        Measures quality and coverage of supporting documents.
        
        Factors:
        - Evidence ratio (% of statements backed)
        - Weak evidence rate (% marked as weak quality)
        - OCR confidence (detected amounts/GSTIN accuracy)
        
        Args:
            latest_signals: Latest ComplianceSignal
            business_id: Business ID (used to fetch signals if needed)
        
        Returns:
            Score 0-100 (higher = better evidence)
        """
        if latest_signals is None:
            if business_id is None:
                raise ValueError("Either latest_signals or business_id required")
            latest_signals = ComplianceSignal.query.filter_by(
                business_id=business_id
            ).order_by(ComplianceSignal.signal_date.desc()).first()
        
        if latest_signals is None:
            return 50  # Neutral default
        
        health = 100
        
        # Factor 1: Evidence coverage ratio (must have docs for statements)
        # 0.9-1.0: 0 penalty
        # 0.7-0.9: -10 penalty
        # 0.5-0.7: -20 penalty
        # <0.5: -40 penalty
        if latest_signals.evidence_ratio < 0.5:
            health -= 40
        elif latest_signals.evidence_ratio < 0.7:
            health -= 20
        elif latest_signals.evidence_ratio < 0.9:
            health -= 10
        
        # Factor 2: Evidence quality (weak vs strong)
        # Weak rate >40%: -30
        # Weak rate 20-40%: -15
        # Weak rate <20%: 0
        if latest_signals.weak_evidence_rate > 0.4:
            health -= 30
        elif latest_signals.weak_evidence_rate > 0.2:
            health -= 15
        
        # Clamp to 0-100
        return max(0, min(100, health))
    
    @staticmethod
    def assess_gst_risk(
        business: Business = None,
        estimated_turnover: float = None
    ) -> str:
        """
        Assess GST filing threshold risk.
        
        Classifies business into risk bracket based on estimated annual turnover.
        
        Low: < ₹20L (below most GST thresholds)
        Medium: ₹20L - ₹40L (approaching/in GST filing requirement)
        High: > ₹40L (well above threshold, active GST filer)
        
        Args:
            business: Business model instance
            estimated_turnover: Annual turnover in ₹
        
        Returns:
            Risk level: 'low', 'medium', or 'high'
        """
        if estimated_turnover is None:
            if business is None:
                raise ValueError("Either business or estimated_turnover required")
            estimated_turnover = business.expected_turnover or 0.0
        
        if estimated_turnover < ProfileCalculator.GST_FILING_LOW_LIMIT:
            return ComplianceProfile.GSTRiskLevel.LOW.value
        elif estimated_turnover < ProfileCalculator.GST_FILING_HIGH_LIMIT:
            return ComplianceProfile.GSTRiskLevel.MEDIUM.value
        else:
            return ComplianceProfile.GSTRiskLevel.HIGH.value
    
    @staticmethod
    def update_profile(business_id: int) -> ComplianceProfile:
        """
        Update or create compliance profile for a business.
        
        Called after signals calculated and rules executed.
        Aggregates all metrics into one profile record.
        
        Args:
            business_id: Business ID
        
        Returns:
            Updated ComplianceProfile instance
        """
        # Get business
        business = Business.query.get(business_id)
        if not business:
            raise ValueError(f"Business {business_id} not found")
        
        # Get or create profile
        profile = ComplianceProfile.query.filter_by(business_id=business_id).first()
        if not profile:
            profile = ComplianceProfile(business_id=business_id)
        
        # Get latest signal
        latest_signal = ComplianceSignal.query.filter_by(
            business_id=business_id
        ).order_by(ComplianceSignal.signal_date.desc()).first()
        
        # Get count of open alerts
        open_alerts = ComplianceAlert.query.filter_by(
            business_id=business_id,
            status=ComplianceAlert.AlertStatus.OPEN
        ).count()
        
        # Calculate all scores
        discipline_score = ProfileCalculator.compute_discipline_score(
            business_id, latest_signal, open_alerts
        )
        evidence_health = ProfileCalculator.compute_evidence_health(
            latest_signal, business_id
        )
        gst_risk_level = ProfileCalculator.assess_gst_risk(
            business, business.expected_turnover
        )
        
        # Update profile
        profile.estimated_turnover = business.expected_turnover or 0.0
        profile.discipline_score = discipline_score
        profile.evidence_health = evidence_health
        profile.gst_risk_level = gst_risk_level
        profile.last_updated = datetime.utcnow()
        
        db.session.add(profile)
        db.session.commit()
        
        return profile
