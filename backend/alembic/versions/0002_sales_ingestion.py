"""Add tenant-aware sales ingestion tables."""

import sqlalchemy as sa

from alembic import op

revision = "0002_sales_ingestion"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "import_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("dataset_type", sa.String(50), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("storage_key", sa.String(500), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("total_rows", sa.Integer(), nullable=False),
        sa.Column("successful_rows", sa.Integer(), nullable=False),
        sa.Column("failed_rows", sa.Integer(), nullable=False),
        sa.Column("error_summary", sa.JSON()),
        sa.Column("processing_metadata", sa.JSON()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="CASCADE", name="fk_import_jobs_org"
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], ondelete="RESTRICT", name="fk_import_jobs_creator"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_import_jobs"),
        sa.UniqueConstraint("storage_key", name="uq_import_jobs_storage_key"),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed')", name="valid_import_status"
        ),
        sa.CheckConstraint("dataset_type IN ('sales_history')", name="valid_import_dataset"),
    )
    op.create_index("ix_import_jobs_organization_id", "import_jobs", ["organization_id"])
    op.create_index("ix_import_jobs_created_by", "import_jobs", ["created_by"])
    op.create_table(
        "import_errors",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("import_job_id", sa.Uuid(), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("field_name", sa.String(100)),
        sa.Column("error_code", sa.String(50), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("raw_value", sa.Text()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["import_job_id"], ["import_jobs.id"], ondelete="CASCADE", name="fk_import_errors_job"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_import_errors"),
    )
    op.create_index("ix_import_errors_import_job_id", "import_errors", ["import_job_id"])
    op.create_table(
        "staging_sales_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("import_job_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column("product_code", sa.String(200)),
        sa.Column("sale_date", sa.Date()),
        sa.Column("quantity", sa.Numeric(18, 4)),
        sa.Column("unit_price", sa.Numeric(18, 4)),
        sa.Column("warehouse_code", sa.String(200)),
        sa.Column("is_valid", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["import_job_id"], ["import_jobs.id"], ondelete="CASCADE", name="fk_staging_sales_job"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
            name="fk_staging_sales_org",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_staging_sales_records"),
    )
    op.create_index(
        "ix_staging_sales_records_import_job_id", "staging_sales_records", ["import_job_id"]
    )
    op.create_index(
        "ix_staging_sales_records_organization_id", "staging_sales_records", ["organization_id"]
    )
    op.create_table(
        "sales_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("import_job_id", sa.Uuid(), nullable=False),
        sa.Column("source_row_number", sa.Integer(), nullable=False),
        sa.Column("product_code", sa.String(200), nullable=False),
        sa.Column("sale_date", sa.Date(), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("warehouse_code", sa.String(200), nullable=False),
        sa.Column("row_fingerprint", sa.String(64), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
            name="fk_sales_history_org",
        ),
        sa.ForeignKeyConstraint(
            ["import_job_id"], ["import_jobs.id"], ondelete="RESTRICT", name="fk_sales_history_job"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_sales_history"),
        sa.UniqueConstraint("row_fingerprint", name="uq_sales_history_row_fingerprint"),
    )
    op.create_index("ix_sales_history_organization_id", "sales_history", ["organization_id"])
    op.create_index("ix_sales_history_import_job_id", "sales_history", ["import_job_id"])
    op.create_index("ix_sales_history_org_date", "sales_history", ["organization_id", "sale_date"])
    op.create_index(
        "ix_sales_history_org_product", "sales_history", ["organization_id", "product_code"]
    )


def downgrade() -> None:
    op.drop_table("sales_history")
    op.drop_table("staging_sales_records")
    op.drop_table("import_errors")
    op.drop_table("import_jobs")
