"""feature4_evidence_ocr_001

Add new columns to business_evidence for Feature 4:
  uploaded_by, file_url, thumbnail_url, cloudinary_public_id,
  file_type, file_size_bytes, quality_status, ocr_status,
  ocr_vendor_name, updated_at

All guarded by _col_exists so this is idempotent.

Revision ID: feature4_evidence_ocr_001
Revises: hotfix_evidence_columns_001
Create Date: 2026-02-23
"""
from alembic import op
import sqlalchemy as sa

revision      = "feature4_evidence_ocr_001"
down_revision = "hotfix_evidence_columns_001"
branch_labels = None
depends_on    = None


def _col_exists(table, col):
    bind = op.get_bind()
    return col in [c["name"] for c in sa.inspect(bind).get_columns(table)]


def upgrade():
    new_cols = {
        "uploaded_by":           sa.Column("uploaded_by",           sa.Integer,      nullable=True),
        "file_url":              sa.Column("file_url",              sa.Text,         nullable=True),
        "thumbnail_url":         sa.Column("thumbnail_url",         sa.Text,         nullable=True),
        "cloudinary_public_id":  sa.Column("cloudinary_public_id",  sa.String(255),  nullable=True),
        "file_type":             sa.Column("file_type",             sa.String(50),   nullable=True),
        "file_size_bytes":       sa.Column("file_size_bytes",       sa.Integer,      nullable=True),
        "quality_status":        sa.Column("quality_status",        sa.String(20),   nullable=True),
        "ocr_status":            sa.Column("ocr_status",            sa.String(20),   nullable=True,
                                           server_default="pending"),
        "ocr_vendor_name":       sa.Column("ocr_vendor_name",       sa.String(150),  nullable=True),
        "updated_at":            sa.Column("updated_at",            sa.DateTime,     nullable=True),
    }
    with op.batch_alter_table("business_evidence", schema=None) as batch_op:
        for col_name, col_def in new_cols.items():
            if not _col_exists("business_evidence", col_name):
                batch_op.add_column(col_def)


def downgrade():
    drop = [
        "uploaded_by", "file_url", "thumbnail_url", "cloudinary_public_id",
        "file_type", "file_size_bytes", "quality_status", "ocr_status",
        "ocr_vendor_name", "updated_at",
    ]
    with op.batch_alter_table("business_evidence", schema=None) as batch_op:
        for col in drop:
            if _col_exists("business_evidence", col):
                batch_op.drop_column(col)
