"""hotfix_evidence_columns

Add all missing columns to business_evidence:
  evidence_strength, detected_amount, detected_date, detected_gstin

These are in the model but were never added to the DB.

Revision ID: hotfix_evidence_columns_001
Revises: hotfix_evidence_strength_001
Create Date: 2026-02-23
"""
from alembic import op
import sqlalchemy as sa

revision = "hotfix_evidence_columns_001"
down_revision = "hotfix_evidence_strength_001"
branch_labels = None
depends_on = None


def _col_exists(table, col):
    bind = op.get_bind()
    return col in [c["name"] for c in sa.inspect(bind).get_columns(table)]


def upgrade():
    new_cols = {
        "evidence_strength": sa.Column("evidence_strength", sa.String(20),
                                       nullable=False, server_default="weak"),
        "detected_amount":   sa.Column("detected_amount",   sa.Float,    nullable=True),
        "detected_date":     sa.Column("detected_date",     sa.DateTime, nullable=True),
        "detected_gstin":    sa.Column("detected_gstin",    sa.String(20), nullable=True),
    }
    with op.batch_alter_table("business_evidence", schema=None) as batch_op:
        for col_name, col_def in new_cols.items():
            if not _col_exists("business_evidence", col_name):
                batch_op.add_column(col_def)


def downgrade():
    drop = ["evidence_strength", "detected_amount", "detected_date", "detected_gstin"]
    with op.batch_alter_table("business_evidence", schema=None) as batch_op:
        for col in drop:
            if _col_exists("business_evidence", col):
                batch_op.drop_column(col)
