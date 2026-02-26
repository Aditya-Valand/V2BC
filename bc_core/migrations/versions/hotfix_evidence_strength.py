"""hotfix_evidence_strength

Add evidence_strength column to business_evidence table.
Column is in model but was never added to the DB.

Revision ID: hotfix_evidence_strength_001
Revises: hotfix_user_email_nullable_001
Create Date: 2026-02-23
"""
from alembic import op
import sqlalchemy as sa

revision = "hotfix_evidence_strength_001"
down_revision = "hotfix_user_email_nullable_001"
branch_labels = None
depends_on = None


def _col_exists(table, col):
    bind = op.get_bind()
    return col in [c["name"] for c in sa.inspect(bind).get_columns(table)]


def upgrade():
    with op.batch_alter_table("business_evidence", schema=None) as batch_op:
        if not _col_exists("business_evidence", "evidence_strength"):
            batch_op.add_column(
                sa.Column("evidence_strength", sa.String(20),
                          nullable=False, server_default="weak")
            )


def downgrade():
    with op.batch_alter_table("business_evidence", schema=None) as batch_op:
        if _col_exists("business_evidence", "evidence_strength"):
            batch_op.drop_column("evidence_strength")
