"""Add import processing attempt telemetry."""

import sqlalchemy as sa

from alembic import op

revision = "0007_processing_attempts"
down_revision = "0006_master_data"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "import_processing_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("import_job_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("failure_category", sa.String(length=50), nullable=True),
        sa.Column("duration_seconds", sa.Numeric(12, 3), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["import_job_id"], ["import_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_import_processing_attempts_import_job_id",
        "import_processing_attempts",
        ["import_job_id"],
    )
    op.create_index(
        "ix_import_processing_attempts_organization_id",
        "import_processing_attempts",
        ["organization_id"],
    )
    op.create_index(
        "ix_import_attempts_org_import",
        "import_processing_attempts",
        ["organization_id", "import_job_id"],
    )
    op.create_index(
        "ix_import_attempts_import_started",
        "import_processing_attempts",
        ["import_job_id", "started_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_import_attempts_import_started", table_name="import_processing_attempts")
    op.drop_index("ix_import_attempts_org_import", table_name="import_processing_attempts")
    op.drop_index(
        "ix_import_processing_attempts_organization_id", table_name="import_processing_attempts"
    )
    op.drop_index(
        "ix_import_processing_attempts_import_job_id", table_name="import_processing_attempts"
    )
    op.drop_table("import_processing_attempts")
