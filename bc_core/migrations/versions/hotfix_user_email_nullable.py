"""hotfix_user_email_nullable

Allow user.email to be NULL so phone-only client accounts can be created.

The original table was created with email NOT NULL.  Feature 1 made the
model nullable but the DB constraint was never updated.

Revision ID: hotfix_user_email_nullable_001
Revises: feature2_client_invite_001
Create Date: 2026-02-23
"""
from alembic import op
import sqlalchemy as sa

revision = "hotfix_user_email_nullable_001"
down_revision = "feature2_client_invite_001"
branch_labels = None
depends_on = None


def upgrade():
    # SQLite batch_alter_table recreates the table with updated schema.
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.alter_column(
            "email",
            existing_type=sa.String(120),
            nullable=True,
        )


def downgrade():
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.alter_column(
            "email",
            existing_type=sa.String(120),
            nullable=False,
        )
