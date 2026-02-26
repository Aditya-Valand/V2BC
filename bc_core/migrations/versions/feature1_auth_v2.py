"""feature1_auth_v2

Feature 1 — CA Auth System

Changes
-------
  user table          — add phone, fcm_token, language, is_verified,
                        otp_code, otp_expires_at, otp_attempts,
                        otp_last_sent_at, last_login, updated_at

  organization table  — add city, state, license_number, plan,
                        plan_expires_at, client_count, updated_at

  org_members         — new table (replaces user_organization_permission)

  jwt_blocklist       — new table for logout / token revocation

  user_organization_permission — dropped (superseded by org_members)

Revision ID: feature1_auth_v2_001
Revises: add_phase3_compliance_001
Create Date: 2026-02-23
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "feature1_auth_v2_001"
down_revision = "add_phase3_compliance_001"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # ---------------------------------------------------------------- #
    # user — add new columns
    # ---------------------------------------------------------------- #
    with op.batch_alter_table("user") as batch_op:
        # Check each column before adding to make migration idempotent
        existing_cols = {col["name"] for col in sa.inspect(conn).get_columns("user")}

        if "phone" not in existing_cols:
            batch_op.add_column(sa.Column("phone", sa.String(15), nullable=True))
        if "fcm_token" not in existing_cols:
            batch_op.add_column(sa.Column("fcm_token", sa.Text, nullable=True))
        if "language" not in existing_cols:
            batch_op.add_column(
                sa.Column("language", sa.String(5), nullable=False, server_default="en")
            )
        if "is_verified" not in existing_cols:
            batch_op.add_column(
                sa.Column("is_verified", sa.Boolean, nullable=False, server_default="0")
            )
        if "otp_code" not in existing_cols:
            batch_op.add_column(sa.Column("otp_code", sa.String(10), nullable=True))
        if "otp_expires_at" not in existing_cols:
            batch_op.add_column(sa.Column("otp_expires_at", sa.DateTime, nullable=True))
        if "otp_attempts" not in existing_cols:
            batch_op.add_column(
                sa.Column("otp_attempts", sa.Integer, nullable=False, server_default="0")
            )
        if "otp_last_sent_at" not in existing_cols:
            batch_op.add_column(sa.Column("otp_last_sent_at", sa.DateTime, nullable=True))
        if "last_login" not in existing_cols:
            batch_op.add_column(sa.Column("last_login", sa.DateTime, nullable=True))
        if "updated_at" not in existing_cols:
            batch_op.add_column(
                sa.Column(
                    "updated_at", sa.DateTime, nullable=False,
                    server_default=sa.func.now()
                )
            )

    # Unique index on phone (only non-null values)
    try:
        op.create_index("ix_user_phone", "user", ["phone"], unique=True)
    except Exception:
        pass  # already exists

    # ---------------------------------------------------------------- #
    # organization — add new columns
    # ---------------------------------------------------------------- #
    with op.batch_alter_table("organization") as batch_op:
        existing_cols = {col["name"] for col in sa.inspect(conn).get_columns("organization")}

        if "city" not in existing_cols:
            batch_op.add_column(sa.Column("city", sa.String(100), nullable=True))
        if "state" not in existing_cols:
            batch_op.add_column(sa.Column("state", sa.String(100), nullable=True))
        if "license_number" not in existing_cols:
            batch_op.add_column(sa.Column("license_number", sa.String(50), nullable=True))
        if "plan" not in existing_cols:
            batch_op.add_column(
                sa.Column("plan", sa.String(20), nullable=False, server_default="free")
            )
        if "plan_expires_at" not in existing_cols:
            batch_op.add_column(sa.Column("plan_expires_at", sa.DateTime, nullable=True))
        if "client_count" not in existing_cols:
            batch_op.add_column(
                sa.Column("client_count", sa.Integer, nullable=False, server_default="0")
            )
        if "updated_at" not in existing_cols:
            batch_op.add_column(
                sa.Column(
                    "updated_at", sa.DateTime, nullable=False,
                    server_default=sa.func.now()
                )
            )

    # ---------------------------------------------------------------- #
    # org_members — new table
    # ---------------------------------------------------------------- #
    existing_tables = sa.inspect(conn).get_table_names()

    if "org_members" not in existing_tables:
        op.create_table(
            "org_members",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column(
                "user_id", sa.Integer,
                sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=False
            ),
            sa.Column(
                "org_id", sa.Integer,
                sa.ForeignKey("organization.id", ondelete="CASCADE"), nullable=False
            ),
            sa.Column(
                "role", sa.String(20), nullable=False, server_default="staff"
            ),
            sa.Column(
                "created_at", sa.DateTime, nullable=False,
                server_default=sa.func.now()
            ),
            sa.UniqueConstraint("user_id", "org_id", name="uq_org_member_user_org"),
        )
        op.create_index("ix_org_members_user_id", "org_members", ["user_id"])
        op.create_index("ix_org_members_org_id",  "org_members", ["org_id"])

    # ---------------------------------------------------------------- #
    # jwt_blocklist — new table
    # ---------------------------------------------------------------- #
    if "jwt_blocklist" not in existing_tables:
        op.create_table(
            "jwt_blocklist",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("jti", sa.String(36), nullable=False, unique=True),
            sa.Column("token_type", sa.String(10), nullable=False),
            sa.Column("expires_at", sa.DateTime, nullable=False),
            sa.Column(
                "created_at", sa.DateTime, nullable=False,
                server_default=sa.func.now()
            ),
        )
        op.create_index("ix_jwt_blocklist_jti", "jwt_blocklist", ["jti"], unique=True)

    # ---------------------------------------------------------------- #
    # Drop old permission table (superseded by org_members)
    # ---------------------------------------------------------------- #
    if "user_organization_permission" in existing_tables:
        op.drop_table("user_organization_permission")


def downgrade():
    conn = op.get_bind()
    existing_tables = sa.inspect(conn).get_table_names()

    # Drop new tables
    if "jwt_blocklist" in existing_tables:
        op.drop_index("ix_jwt_blocklist_jti", table_name="jwt_blocklist")
        op.drop_table("jwt_blocklist")

    if "org_members" in existing_tables:
        op.drop_index("ix_org_members_org_id",  table_name="org_members")
        op.drop_index("ix_org_members_user_id", table_name="org_members")
        op.drop_table("org_members")

    # Restore old permission table
    if "user_organization_permission" not in existing_tables:
        op.create_table(
            "user_organization_permission",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("user_id", sa.Integer, sa.ForeignKey("user.id"), nullable=False),
            sa.Column("organization_id", sa.Integer, sa.ForeignKey("organization.id"), nullable=False),
            sa.Column("role", sa.String(50), server_default="staff"),
            sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
            sa.UniqueConstraint("user_id", "organization_id", name="uq_user_org"),
        )

    # Remove added columns from organization
    with op.batch_alter_table("organization") as batch_op:
        for col in ("updated_at", "client_count", "plan_expires_at", "plan",
                    "license_number", "state", "city"):
            try:
                batch_op.drop_column(col)
            except Exception:
                pass

    # Remove added columns from user
    try:
        op.drop_index("ix_user_phone", table_name="user")
    except Exception:
        pass

    with op.batch_alter_table("user") as batch_op:
        for col in ("updated_at", "last_login", "otp_last_sent_at", "otp_attempts",
                    "otp_expires_at", "otp_code", "is_verified", "language",
                    "fcm_token", "phone"):
            try:
                batch_op.drop_column(col)
            except Exception:
                pass
