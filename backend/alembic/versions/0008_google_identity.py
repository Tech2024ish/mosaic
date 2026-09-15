"""Add Google identity linkage for authenticated users."""

import sqlalchemy as sa

from alembic import op

revision = "0008_google_identity"
down_revision = "0007_processing_attempts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("google_subject", sa.String(length=255), nullable=True))
    op.alter_column("users", "password_hash", existing_type=sa.String(length=255), nullable=True)
    op.create_unique_constraint("uq_users_google_subject", "users", ["google_subject"])


def downgrade() -> None:
    op.drop_constraint("uq_users_google_subject", "users", type_="unique")
    op.execute("UPDATE users SET password_hash = '!google-oauth-only!' WHERE password_hash IS NULL")
    op.alter_column("users", "password_hash", existing_type=sa.String(length=255), nullable=False)
    op.drop_column("users", "google_subject")
