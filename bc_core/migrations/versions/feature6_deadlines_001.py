"""feature6_deadlines_001

Create compliance_deadline table for Feature 6:
  Compliance Calendar + Deadline Management.

Idempotent — checks table existence before creating.

Revision ID: feature6_deadlines_001
Revises: feature4_evidence_ocr_001
Create Date: 2026-02-26
"""
from alembic import op
import sqlalchemy as sa


revision = "feature6_deadlines_001"
down_revision = "feature4_evidence_ocr_001"
branch_labels = None
depends_on = None


def _table_exists(table_name):
    """Check if a table already exists (SQLite + PostgreSQL safe)."""
    conn = op.get_bind()
    dialect = conn.dialect.name
    if dialect == "sqlite":
        result = conn.execute(
            sa.text("SELECT name FROM sqlite_master WHERE type='table' AND name=:t"),
            {"t": table_name},
        )
        return result.fetchone() is not None
    else:
        result = conn.execute(
            sa.text(
                "SELECT EXISTS (SELECT FROM information_schema.tables "
                "WHERE table_name = :t)"
            ),
            {"t": table_name},
        )
        return result.scalar()


def upgrade():
    if _table_exists("compliance_deadline"):
        return

    op.create_table(
        "compliance_deadline",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "client_id", sa.Integer,
            sa.ForeignKey("business.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "org_id", sa.Integer,
            sa.ForeignKey("organization.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("deadline_type", sa.String(50), nullable=False),
        sa.Column("description", sa.String(200), nullable=True),
        sa.Column("due_date", sa.Date, nullable=False),
        sa.Column("period_start", sa.Date, nullable=True),
        sa.Column("period_end", sa.Date, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("reminder_sent_at", sa.DateTime, nullable=True),
        sa.Column("acknowledged_at", sa.DateTime, nullable=True),
        sa.Column("completed_at", sa.DateTime, nullable=True),
        sa.Column(
            "completed_by", sa.Integer,
            sa.ForeignKey("user.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False,
                  server_default=sa.func.now()),
    )

    op.create_index("idx_deadline_client_id", "compliance_deadline", ["client_id"])
    op.create_index("idx_deadline_due_date", "compliance_deadline", ["due_date"])
    op.create_index("idx_deadline_status", "compliance_deadline", ["status"])
    op.create_index("idx_deadline_org_id", "compliance_deadline", ["org_id"])


def downgrade():
    op.drop_index("idx_deadline_org_id", table_name="compliance_deadline")
    op.drop_index("idx_deadline_status", table_name="compliance_deadline")
    op.drop_index("idx_deadline_due_date", table_name="compliance_deadline")
    op.drop_index("idx_deadline_client_id", table_name="compliance_deadline")
    op.drop_table("compliance_deadline")
