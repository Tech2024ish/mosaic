"""Add import cancellation and operational event history."""

import sqlalchemy as sa

from alembic import op

revision = "0005_import_operations"
down_revision = "0004_auth_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("valid_import_status", "import_jobs", type_="check")
    op.create_check_constraint(
        "valid_import_status",
        "import_jobs",
        "status IN ('pending', 'processing', 'completed', 'failed', 'cancelled')",
    )
    op.create_table(
        "import_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("import_job_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["import_job_id"], ["import_jobs.id"], ondelete="CASCADE", name="fk_import_events_job"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
            name="fk_import_events_org",
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"], ["users.id"], ondelete="SET NULL", name="fk_import_events_actor"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_import_events"),
    )
    op.create_index("ix_import_events_import_job_id", "import_events", ["import_job_id"])
    op.create_index("ix_import_events_organization_id", "import_events", ["organization_id"])
    op.create_index(
        "ix_import_events_org_created", "import_events", ["organization_id", "created_at"]
    )
    op.create_index(
        "ix_import_events_import_created", "import_events", ["import_job_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_import_events_import_created", table_name="import_events")
    op.drop_index("ix_import_events_org_created", table_name="import_events")
    op.drop_index("ix_import_events_organization_id", table_name="import_events")
    op.drop_index("ix_import_events_import_job_id", table_name="import_events")
    op.drop_table("import_events")
    op.drop_constraint("valid_import_status", "import_jobs", type_="check")
    op.create_check_constraint(
        "valid_import_status",
        "import_jobs",
        "status IN ('pending', 'processing', 'completed', 'failed')",
    )
