"""Add tenant-owned master data and inventory snapshots."""

import sqlalchemy as sa

from alembic import op

revision = "0006_master_data"
down_revision = "0005_import_operations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("valid_import_dataset", "import_jobs", type_="check")
    op.create_check_constraint(
        "valid_import_dataset",
        "import_jobs",
        "dataset_type IN ('sales_history', 'products', 'warehouses', 'suppliers', 'inventory_snapshots')",
    )
    for table, code in (
        ("products", "product_code"),
        ("warehouses", "warehouse_code"),
        ("suppliers", "supplier_code"),
    ):
        op.create_table(
            table,
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("organization_id", sa.Uuid(), nullable=False),
            sa.Column(code, sa.String(200), nullable=False),
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("organization_id", code),
        )
        op.create_index(f"ix_{table}_organization_id", table, ["organization_id"])
    op.add_column("products", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("products", sa.Column("category", sa.String(200), nullable=True))
    op.add_column("products", sa.Column("unit_of_measure", sa.String(50), nullable=True))
    op.add_column("warehouses", sa.Column("location", sa.String(200), nullable=True))
    op.add_column("suppliers", sa.Column("contact_name", sa.String(200), nullable=True))
    op.add_column("suppliers", sa.Column("contact_email", sa.String(320), nullable=True))
    op.add_column("suppliers", sa.Column("contact_phone", sa.String(50), nullable=True))
    for table in ("products", "warehouses", "suppliers"):
        op.alter_column(table, "is_active", server_default=None)
    op.create_table(
        "inventory_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("warehouse_id", sa.Uuid(), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("quantity_on_hand", sa.Numeric(18, 4), nullable=False),
        sa.Column("unit_cost", sa.Numeric(18, 4), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "product_id", "warehouse_id", "snapshot_date"),
    )
    for column in ("organization_id", "product_id", "warehouse_id", "snapshot_date"):
        op.create_index(f"ix_inventory_snapshots_{column}", "inventory_snapshots", [column])


def downgrade() -> None:
    for column in ("snapshot_date", "warehouse_id", "product_id", "organization_id"):
        op.drop_index(f"ix_inventory_snapshots_{column}", table_name="inventory_snapshots")
    op.drop_table("inventory_snapshots")
    op.drop_column("warehouses", "location")
    op.drop_column("products", "unit_of_measure")
    op.drop_column("products", "category")
    op.drop_column("products", "description")
    op.drop_column("suppliers", "contact_phone")
    op.drop_column("suppliers", "contact_email")
    op.drop_column("suppliers", "contact_name")
    for table in ("suppliers", "warehouses", "products"):
        op.drop_index(f"ix_{table}_organization_id", table_name=table)
        op.drop_table(table)
    op.drop_constraint("valid_import_dataset", "import_jobs", type_="check")
    op.create_check_constraint(
        "valid_import_dataset", "import_jobs", "dataset_type IN ('sales_history')"
    )
