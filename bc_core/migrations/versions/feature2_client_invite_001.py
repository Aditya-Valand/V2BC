"""feature2_client_invite_001

Feature 2 — Client Invite + Client PWA Registration

Changes
-------
  business table  — add invite_code, invite_status, invite_expires_at,
                    owner_user_id, whatsapp_phone, phone, is_active, updated_at

Revision ID: feature2_client_invite_001
Revises: feature1_auth_v2_001
Create Date: 2026-02-23
"""
from alembic import op
import sqlalchemy as sa

revision = "feature2_client_invite_001"
down_revision = "feature1_auth_v2_001"
branch_labels = None
depends_on = None


def _col_exists(table, col):
    bind = op.get_bind()
    return col in [c["name"] for c in sa.inspect(bind).get_columns(table)]


def _idx_exists(table, name):
    bind = op.get_bind()
    return name in [i["name"] for i in sa.inspect(bind).get_indexes(table)]


def upgrade():
    # SQLite batch mode: add columns one by one, no FK constraint in DDL
    # (SQLite ignores FK enforcement unless PRAGMA foreign_keys=ON; the
    #  application layer enforces the relationship.)
    cols = {
        "invite_code":       sa.Column("invite_code",       sa.String(12),  nullable=True),
        "invite_status":     sa.Column("invite_status",     sa.String(20),  nullable=False, server_default="pending"),
        "invite_expires_at": sa.Column("invite_expires_at", sa.DateTime,    nullable=True),
        "owner_user_id":     sa.Column("owner_user_id",     sa.Integer,     nullable=True),
        "whatsapp_phone":    sa.Column("whatsapp_phone",    sa.String(20),  nullable=True),
        "phone":             sa.Column("phone",             sa.String(15),  nullable=True),
        "is_active":         sa.Column("is_active",         sa.Boolean,     nullable=False, server_default=sa.true()),
        "updated_at":        sa.Column("updated_at",        sa.DateTime,    nullable=True),
    }

    with op.batch_alter_table("business", schema=None) as batch_op:
        for col_name, col_def in cols.items():
            if not _col_exists("business", col_name):
                batch_op.add_column(col_def)

    if not _idx_exists("business", "uq_business_invite_code"):
        op.create_index("uq_business_invite_code",    "business", ["invite_code"],    unique=True)
    if not _idx_exists("business", "uq_business_whatsapp_phone"):
        op.create_index("uq_business_whatsapp_phone", "business", ["whatsapp_phone"], unique=True)


def downgrade():
    for idx in ("uq_business_invite_code", "uq_business_whatsapp_phone"):
        if _idx_exists("business", idx):
            op.drop_index(idx, table_name="business")

    drop_cols = ["invite_code", "invite_status", "invite_expires_at",
                 "owner_user_id", "whatsapp_phone", "phone", "is_active", "updated_at"]
    with op.batch_alter_table("business", schema=None) as batch_op:
        for col in drop_cols:
            if _col_exists("business", col):
                batch_op.drop_column(col)
