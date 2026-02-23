"""add_compliance_phase3_models

Phase-3 Compliance & Risk Engine
Adds three new tables for signals, profiles, and alerts.

Revision ID: add_phase3_compliance_001
Revises: 
Create Date: 2024-01-15

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = 'add_phase3_compliance_001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Create Phase-3 compliance tables."""
    
    # Create compliance_signal table
    try:
        op.create_table(
            'compliance_signal',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('business_id', sa.Integer(), nullable=False),
            sa.Column('signal_date', sa.DateTime(), nullable=False),
            sa.Column('daily_turnover', sa.Float(), nullable=False),
            sa.Column('monthly_turnover', sa.Float(), nullable=False),
            sa.Column('evidence_ratio', sa.Float(), nullable=False),
            sa.Column('weak_evidence_rate', sa.Float(), nullable=False),
            sa.Column('silence_days', sa.Integer(), nullable=False),
            sa.Column('abnormal_spike_flag', sa.Boolean(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['business_id'], ['business.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('business_id', 'signal_date', name='uq_business_signal_date'),
        )
        op.create_index('idx_business_signal_date', 'compliance_signal', ['business_id', 'signal_date'])
        op.create_index('idx_signal_spike', 'compliance_signal', ['business_id', 'abnormal_spike_flag'])
    except Exception:
        pass
    
    # Create compliance_profile table
    try:
        op.create_table(
            'compliance_profile',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('business_id', sa.Integer(), nullable=False),
            sa.Column('estimated_turnover', sa.Float(), nullable=False),
            sa.Column('discipline_score', sa.Integer(), nullable=False),
            sa.Column('evidence_health', sa.Integer(), nullable=False),
            sa.Column('gst_risk_level', sa.String(50), nullable=False),
            sa.Column('last_updated', sa.DateTime(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['business_id'], ['business.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('business_id', name='uq_business_profile'),
        )
        op.create_index('idx_profile_discipline', 'compliance_profile', ['discipline_score'])
        op.create_index('idx_profile_gst_risk', 'compliance_profile', ['gst_risk_level'])
    except Exception:
        pass
    
    # Create compliance_alert table
    try:
        op.create_table(
            'compliance_alert',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('business_id', sa.Integer(), nullable=False),
            sa.Column('alert_type', sa.String(50), nullable=False),
            sa.Column('severity', sa.String(50), nullable=False),
            sa.Column('reason', sa.String(500), nullable=False),
            sa.Column('rule_that_triggered', sa.String(100), nullable=False),
            sa.Column('status', sa.String(50), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('resolved_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['business_id'], ['business.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('idx_alert_business_status', 'compliance_alert', ['business_id', 'status'])
        op.create_index('idx_alert_severity', 'compliance_alert', ['severity'])
        op.create_index('idx_alert_type', 'compliance_alert', ['alert_type'])
        op.create_index('idx_alert_created', 'compliance_alert', ['created_at'])
    except Exception:
        pass


def downgrade():
    """Drop Phase-3 compliance tables."""
    try:
        op.drop_index('idx_alert_created', table_name='compliance_alert')
        op.drop_index('idx_alert_type', table_name='compliance_alert')
        op.drop_index('idx_alert_severity', table_name='compliance_alert')
        op.drop_index('idx_alert_business_status', table_name='compliance_alert')
        op.drop_table('compliance_alert')
    except Exception:
        pass
    
    try:
        op.drop_index('idx_profile_gst_risk', table_name='compliance_profile')
        op.drop_index('idx_profile_discipline', table_name='compliance_profile')
        op.drop_table('compliance_profile')
    except Exception:
        pass
    
    try:
        op.drop_index('idx_signal_spike', table_name='compliance_signal')
        op.drop_index('idx_business_signal_date', table_name='compliance_signal')
        op.drop_table('compliance_signal')
    except Exception:
        pass
