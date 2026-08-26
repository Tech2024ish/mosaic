"""Add user profile name and normalized email uniqueness."""

import sqlalchemy as sa

from alembic import op

revision = "0003_auth_user_profile"
down_revision = "0002_sales_ingestion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users", sa.Column("name", sa.String(length=200), nullable=False, server_default="")
    )
    op.alter_column("users", "name", server_default=None)
    op.drop_index("ix_users_email", table_name="users")
    op.create_unique_constraint("uq_users_email", "users", ["email"])


def downgrade() -> None:
    op.drop_constraint("uq_users_email", "users", type_="unique")
    op.create_index("ix_users_email", "users", ["email"])
    op.drop_column("users", "name")
