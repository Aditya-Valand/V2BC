"""
Compliance Module Models

Phase-3: Compliance & Risk Engine
Provides data structures for signals, profiles, and alerts.

Architecture:
- ComplianceSignal: Immutable daily metrics (read-only, never updated)
- ComplianceProfile: System-generated business view (updated as signals arrive)
- ComplianceAlert: Alert tracking (created by rule engine only)
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, Float, String, DateTime, Boolean, 
    ForeignKey, Index, Enum, CheckConstraint, UniqueConstraint
)
from sqlalchemy.orm import relationship
from core.extensions import db
import enum


class ComplianceSignal(db.Model):
    """
    Daily compliance signal for a business.
    
    Stores calculated metrics derived from statements and evidence.
    Immutable: once created, never updated.
    One record per business per day.
    
    Metrics:
    - daily_turnover: Sum of sales today (₹)
    - monthly_turnover: Sum of sales this month (₹)
    - evidence_ratio: Statements with backing / Total statements (0-1)
    - weak_evidence_rate: Weak evidence count / Total evidence (0-1)
    - silence_days: Days since last statement
    - abnormal_spike_flag: True if today's sales > 2.5x monthly average
    """
    
    __tablename__ = 'compliance_signal'
    
    id = Column(Integer, primary_key=True)
    business_id = Column(Integer, ForeignKey('business.id', ondelete='CASCADE'), nullable=False, index=True)
    signal_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Turnover metrics (₹)
    daily_turnover = Column(Float, nullable=False, default=0.0)  # Today's sales sum
    monthly_turnover = Column(Float, nullable=False, default=0.0)  # This month's sales sum
    
    # Evidence quality metrics (0-1)
    evidence_ratio = Column(Float, nullable=False, default=0.0)  # % of statements with backing
    weak_evidence_rate = Column(Float, nullable=False, default=0.0)  # % of evidence marked weak
    
    # Behavioral metrics
    silence_days = Column(Integer, nullable=False, default=0)  # Days since last statement
    abnormal_spike_flag = Column(Boolean, nullable=False, default=False)  # Sales spike detected
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    business = relationship('Business', foreign_keys=[business_id], lazy='joined')
    
    # Unique constraint: one signal per business per day
    __table_args__ = (
        UniqueConstraint('business_id', 'signal_date', name='uq_business_signal_date'),
        Index('idx_business_signal_date', 'business_id', 'signal_date'),
        Index('idx_signal_spike', 'business_id', 'abnormal_spike_flag'),
        # Ensure metrics are within valid ranges
        CheckConstraint('evidence_ratio >= 0.0 AND evidence_ratio <= 1.0', name='ck_evidence_ratio_range'),
        CheckConstraint('weak_evidence_rate >= 0.0 AND weak_evidence_rate <= 1.0', name='ck_weak_evidence_range'),
        CheckConstraint('daily_turnover >= 0.0', name='ck_daily_turnover_positive'),
        CheckConstraint('monthly_turnover >= 0.0', name='ck_monthly_turnover_positive'),
        CheckConstraint('silence_days >= 0', name='ck_silence_days_positive'),
    )
    
    def __repr__(self):
        return f'<ComplianceSignal {self.business_id} {self.signal_date.date()}>'


class ComplianceProfile(db.Model):
    """
    System-generated compliance profile for a business.
    
    Aggregated view computed from signals and alerts.
    Updated whenever signals change or alerts are created/resolved.
    One record per business (unique).
    
    Scores:
    - discipline_score: 0-100 (higher = more compliant)
    - evidence_health: 0-100 (higher = better backed)
    - gst_risk_level: low (<20L), medium (20-40L), high (>40L estimated turnover)
    """
    
    __tablename__ = 'compliance_profile'
    
    class GSTRiskLevel(enum.Enum):
        """GST filing threshold risk levels based on estimated turnover"""
        LOW = 'low'          # < 20L annual
        MEDIUM = 'medium'    # 20-40L annual
        HIGH = 'high'        # > 40L annual
    
    id = Column(Integer, primary_key=True)
    business_id = Column(Integer, ForeignKey('business.id', ondelete='CASCADE'), nullable=False, unique=True, index=True)
    
    # Estimated turnover from business metadata (₹)
    estimated_turnover = Column(Float, nullable=False, default=0.0)
    
    # Compliance scores (0-100)
    discipline_score = Column(Integer, nullable=False, default=50)  # 0-100, higher is better
    evidence_health = Column(Integer, nullable=False, default=50)   # 0-100, higher is better
    
    # GST filing threshold classification
    gst_risk_level = Column(
        Enum(GSTRiskLevel),
        nullable=False,
        default=GSTRiskLevel.LOW,
        comment='Estimated turnover bracket for GST filing requirements'
    )
    
    last_updated = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    business = relationship('Business', foreign_keys=[business_id], lazy='joined')
    
    __table_args__ = (
        Index('idx_profile_discipline', 'discipline_score'),
        Index('idx_profile_gst_risk', 'gst_risk_level'),
        # Ensure scores are valid
        CheckConstraint('discipline_score >= 0 AND discipline_score <= 100', name='ck_discipline_range'),
        CheckConstraint('evidence_health >= 0 AND evidence_health <= 100', name='ck_evidence_health_range'),
        CheckConstraint('estimated_turnover >= 0.0', name='ck_est_turnover_positive'),
    )
    
    def __repr__(self):
        return f'<ComplianceProfile {self.business_id} score={self.discipline_score}>'


class ComplianceAlert(db.Model):
    """
    Compliance alert generated by rule engine.
    
    Immutable audit trail of alerts.
    Created only by rule engine, never directly from routes.
    Can be acknowledged and resolved by CA users.
    
    Alert Types:
    - threshold: Financial thresholds violated (turnover, GST limit)
    - data_quality: Evidence or statement quality issues
    - behavior: Unusual patterns (spikes, silence)
    - audit_readiness: Business not prepared for audit
    
    Severity levels:
    - critical: Immediate action required (regulatory risk)
    - high: Urgent attention needed
    - medium: Should be addressed
    - low: Informational
    """
    
    __tablename__ = 'compliance_alert'
    
    class AlertType(enum.Enum):
        """Types of compliance alerts"""
        THRESHOLD = 'threshold'          # Turnover/threshold violations
        DATA_QUALITY = 'data_quality'    # Evidence/statement quality issues
        BEHAVIOR = 'behavior'            # Abnormal patterns
        AUDIT_READINESS = 'audit_readiness'  # Audit preparation issues
    
    class AlertSeverity(enum.Enum):
        """Alert severity levels"""
        CRITICAL = 'critical'    # Regulatory risk
        HIGH = 'high'            # Urgent
        MEDIUM = 'medium'        # Important
        LOW = 'low'              # Informational
    
    class AlertStatus(enum.Enum):
        """Alert lifecycle status"""
        OPEN = 'open'                # Active, not yet reviewed
        ACKNOWLEDGED = 'acknowledged'  # CA has seen it
        RESOLVED = 'resolved'        # CA marked as resolved
    
    id = Column(Integer, primary_key=True)
    business_id = Column(Integer, ForeignKey('business.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Alert classification
    alert_type = Column(
        Enum(AlertType),
        nullable=False,
        comment='Category of alert'
    )
    
    severity = Column(
        Enum(AlertSeverity),
        nullable=False,
        comment='How urgent this alert is'
    )
    
    # Alert content
    reason = Column(String(500), nullable=False, comment='Why alert was triggered')
    rule_that_triggered = Column(String(100), nullable=False, comment='Name of rule that created alert')
    
    # Alert status
    status = Column(
        Enum(AlertStatus),
        nullable=False,
        default=AlertStatus.OPEN,
        index=True,
        comment='Current lifecycle state'
    )
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    resolved_at = Column(DateTime, nullable=True, comment='When CA marked as resolved')
    
    # Relationships
    business = relationship('Business', foreign_keys=[business_id], lazy='joined')
    
    __table_args__ = (
        Index('idx_alert_business_status', 'business_id', 'status'),
        Index('idx_alert_severity', 'severity'),
        Index('idx_alert_type', 'alert_type'),
        Index('idx_alert_created', 'created_at'),
    )
    
    def __repr__(self):
        return f'<ComplianceAlert {self.business_id} {self.alert_type.value} {self.severity.value}>'
