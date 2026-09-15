import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import Select, and_, case, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.inventory_snapshot import InventorySnapshot
from app.models.product import Product
from app.models.supplier import Supplier
from app.models.warehouse import Warehouse
from app.schemas.master_data import (
    InventoryProductInsight,
    InventoryStatus,
    InventorySummaryResponse,
    InventoryWarehouseInsight,
)


class MasterDataConflict(ValueError):
    pass


def _commit[RecordT](db: Session, item: RecordT) -> RecordT:
    db.add(item)
    try:
        db.commit()
        db.refresh(item)
    except IntegrityError as exc:
        db.rollback()
        raise MasterDataConflict("A record with this code or snapshot already exists") from exc
    return item


def list_products(
    db: Session,
    organization_id: uuid.UUID,
    offset: int,
    limit: int,
    search: str | None = None,
    sort: str = "code",
    descending: bool = False,
) -> list[Product]:
    sort_columns = {
        "code": Product.product_code,
        "name": Product.name,
        "created_at": Product.created_at,
    }
    column = sort_columns[sort]
    statement: Select[tuple[Product]] = select(Product).where(
        Product.organization_id == organization_id
    )
    if search:
        term = f"%{search.strip()}%"
        statement = statement.where(Product.product_code.ilike(term) | Product.name.ilike(term))
    statement = statement.order_by(column.desc() if descending else column, Product.id)
    return list(db.scalars(statement.offset(offset).limit(limit)))


def get_product(db: Session, organization_id: uuid.UUID, product_id: uuid.UUID) -> Product | None:
    return db.scalar(
        select(Product).where(Product.id == product_id, Product.organization_id == organization_id)
    )


def create_product(db: Session, organization_id: uuid.UUID, data: dict[str, object]) -> Product:
    return _commit(db, Product(organization_id=organization_id, **data))


def update_product(db: Session, product: Product, data: dict[str, object]) -> Product:
    for key, value in data.items():
        if value is not None:
            setattr(product, key, value)
    return _commit(db, product)


def list_warehouses(
    db: Session,
    organization_id: uuid.UUID,
    offset: int,
    limit: int,
    search: str | None = None,
    sort: str = "code",
    descending: bool = False,
) -> list[Warehouse]:
    sort_columns = {
        "code": Warehouse.warehouse_code,
        "name": Warehouse.name,
        "created_at": Warehouse.created_at,
    }
    column = sort_columns[sort]
    statement: Select[tuple[Warehouse]] = select(Warehouse).where(
        Warehouse.organization_id == organization_id
    )
    if search:
        term = f"%{search.strip()}%"
        statement = statement.where(
            Warehouse.warehouse_code.ilike(term)
            | Warehouse.name.ilike(term)
            | Warehouse.location.ilike(term)
        )
    statement = statement.order_by(column.desc() if descending else column, Warehouse.id)
    return list(db.scalars(statement.offset(offset).limit(limit)))


def get_warehouse(
    db: Session, organization_id: uuid.UUID, warehouse_id: uuid.UUID
) -> Warehouse | None:
    return db.scalar(
        select(Warehouse).where(
            Warehouse.id == warehouse_id, Warehouse.organization_id == organization_id
        )
    )


def create_warehouse(db: Session, organization_id: uuid.UUID, data: dict[str, object]) -> Warehouse:
    return _commit(db, Warehouse(organization_id=organization_id, **data))


def update_warehouse(db: Session, warehouse: Warehouse, data: dict[str, object]) -> Warehouse:
    for key, value in data.items():
        if value is not None:
            setattr(warehouse, key, value)
    return _commit(db, warehouse)


def list_suppliers(
    db: Session,
    organization_id: uuid.UUID,
    offset: int,
    limit: int,
    search: str | None = None,
    sort: str = "code",
    descending: bool = False,
) -> list[Supplier]:
    sort_columns = {
        "code": Supplier.supplier_code,
        "name": Supplier.name,
        "created_at": Supplier.created_at,
    }
    column = sort_columns[sort]
    statement: Select[tuple[Supplier]] = select(Supplier).where(
        Supplier.organization_id == organization_id
    )
    if search:
        term = f"%{search.strip()}%"
        statement = statement.where(Supplier.supplier_code.ilike(term) | Supplier.name.ilike(term))
    statement = statement.order_by(column.desc() if descending else column, Supplier.id)
    return list(db.scalars(statement.offset(offset).limit(limit)))


def get_supplier(
    db: Session, organization_id: uuid.UUID, supplier_id: uuid.UUID
) -> Supplier | None:
    return db.scalar(
        select(Supplier).where(
            Supplier.id == supplier_id, Supplier.organization_id == organization_id
        )
    )


def create_supplier(db: Session, organization_id: uuid.UUID, data: dict[str, object]) -> Supplier:
    return _commit(db, Supplier(organization_id=organization_id, **data))


def update_supplier(db: Session, supplier: Supplier, data: dict[str, object]) -> Supplier:
    for key, value in data.items():
        if value is not None:
            setattr(supplier, key, value)
    return _commit(db, supplier)


def list_inventory(
    db: Session,
    organization_id: uuid.UUID,
    offset: int,
    limit: int,
    product_id: uuid.UUID | None = None,
    warehouse_id: uuid.UUID | None = None,
    snapshot_date_from: object | None = None,
    snapshot_date_to: object | None = None,
    sort: str = "snapshot_date",
    descending: bool = True,
) -> list[InventorySnapshot]:
    sort_columns = {
        "snapshot_date": InventorySnapshot.snapshot_date,
        "created_at": InventorySnapshot.created_at,
        "quantity": InventorySnapshot.quantity_on_hand,
    }
    column = sort_columns[sort]
    statement: Select[tuple[InventorySnapshot]] = select(InventorySnapshot).where(
        InventorySnapshot.organization_id == organization_id
    )
    if product_id is not None:
        statement = statement.where(InventorySnapshot.product_id == product_id)
    if warehouse_id is not None:
        statement = statement.where(InventorySnapshot.warehouse_id == warehouse_id)
    if snapshot_date_from is not None:
        statement = statement.where(InventorySnapshot.snapshot_date >= snapshot_date_from)
    if snapshot_date_to is not None:
        statement = statement.where(InventorySnapshot.snapshot_date <= snapshot_date_to)
    statement = statement.order_by(column.desc() if descending else column, InventorySnapshot.id)
    return list(db.scalars(statement.offset(offset).limit(limit)))


def get_inventory(
    db: Session, organization_id: uuid.UUID, snapshot_id: uuid.UUID
) -> InventorySnapshot | None:
    return db.scalar(
        select(InventorySnapshot).where(
            InventorySnapshot.id == snapshot_id,
            InventorySnapshot.organization_id == organization_id,
        )
    )


def create_inventory(
    db: Session, organization_id: uuid.UUID, data: dict[str, object]
) -> InventorySnapshot:
    product = db.scalar(
        select(Product).where(
            Product.id == data["product_id"], Product.organization_id == organization_id
        )
    )
    warehouse = db.scalar(
        select(Warehouse).where(
            Warehouse.id == data["warehouse_id"], Warehouse.organization_id == organization_id
        )
    )
    if product is None or warehouse is None:
        raise MasterDataConflict("Product and warehouse must belong to this organization")
    return _commit(db, InventorySnapshot(organization_id=organization_id, **data))


def _latest_inventory_subquery(organization_id: uuid.UUID) -> Any:
    latest_dates = (
        select(
            InventorySnapshot.product_id,
            InventorySnapshot.warehouse_id,
            func.max(InventorySnapshot.snapshot_date).label("latest_date"),
        )
        .where(InventorySnapshot.organization_id == organization_id)
        .group_by(InventorySnapshot.product_id, InventorySnapshot.warehouse_id)
        .subquery()
    )
    return (
        select(
            InventorySnapshot.product_id,
            InventorySnapshot.warehouse_id,
            InventorySnapshot.quantity_on_hand,
        )
        .join(
            latest_dates,
            and_(
                InventorySnapshot.product_id == latest_dates.c.product_id,
                InventorySnapshot.warehouse_id == latest_dates.c.warehouse_id,
                InventorySnapshot.snapshot_date == latest_dates.c.latest_date,
            ),
        )
        .where(InventorySnapshot.organization_id == organization_id)
        .subquery()
    )


def _inventory_status(quantity: Decimal) -> InventoryStatus:
    return InventoryStatus.IN_STOCK if quantity > 0 else InventoryStatus.OUT_OF_STOCK


def inventory_summary(db: Session, organization_id: uuid.UUID) -> InventorySummaryResponse:
    latest = _latest_inventory_subquery(organization_id)
    product_totals = (
        select(
            Product.id.label("product_id"),
            func.coalesce(func.sum(latest.c.quantity_on_hand), 0).label("total_quantity"),
        )
        .outerjoin(latest, latest.c.product_id == Product.id)
        .where(Product.organization_id == organization_id)
        .group_by(Product.id)
        .subquery()
    )
    row = db.execute(
        select(
            func.coalesce(func.sum(product_totals.c.total_quantity), 0),
            func.count(case((product_totals.c.total_quantity > 0, 1))),
            func.count(case((product_totals.c.total_quantity <= 0, 1))),
        )
    ).one()
    warehouses_with_inventory = db.scalar(
        select(func.count(func.distinct(latest.c.warehouse_id))).where(
            latest.c.quantity_on_hand > 0
        )
    )
    return InventorySummaryResponse(
        total_inventory_units=Decimal(str(row[0] or 0)),
        products_with_inventory=int(row[1]),
        warehouses_with_inventory=int(warehouses_with_inventory or 0),
        out_of_stock_products=int(row[2]),
    )


def inventory_by_warehouse(
    db: Session,
    organization_id: uuid.UUID,
    offset: int,
    limit: int,
    search: str | None = None,
    descending: bool = True,
) -> list[InventoryWarehouseInsight]:
    latest = _latest_inventory_subquery(organization_id)
    total_quantity = func.coalesce(func.sum(latest.c.quantity_on_hand), 0)
    product_count = func.count(func.distinct(latest.c.product_id))
    statement = (
        select(
            Warehouse.id,
            Warehouse.warehouse_code,
            Warehouse.name,
            total_quantity,
            product_count,
        )
        .outerjoin(latest, latest.c.warehouse_id == Warehouse.id)
        .where(Warehouse.organization_id == organization_id)
        .group_by(Warehouse.id, Warehouse.warehouse_code, Warehouse.name)
    )
    if search:
        term = f"%{search.strip()}%"
        statement = statement.where(
            Warehouse.warehouse_code.ilike(term) | Warehouse.name.ilike(term)
        )
    statement = statement.order_by(
        total_quantity.desc() if descending else total_quantity, Warehouse.warehouse_code
    )
    rows = db.execute(statement.offset(offset).limit(limit)).all()
    return [
        InventoryWarehouseInsight(
            warehouse_id=row[0],
            warehouse_code=row[1],
            warehouse_name=row[2],
            total_quantity=Decimal(str(row[3] or 0)),
            product_count=int(row[4]),
            status=_inventory_status(Decimal(str(row[3] or 0))),
        )
        for row in rows
    ]


def inventory_by_product(
    db: Session,
    organization_id: uuid.UUID,
    offset: int,
    limit: int,
    search: str | None = None,
    warehouse_id: uuid.UUID | None = None,
    status: InventoryStatus | None = None,
    sort: str = "quantity",
    descending: bool = True,
) -> list[InventoryProductInsight]:
    latest = _latest_inventory_subquery(organization_id)
    if warehouse_id is not None:
        latest = select(latest).where(latest.c.warehouse_id == warehouse_id).subquery()
    total_quantity = func.coalesce(func.sum(latest.c.quantity_on_hand), 0).label("total_quantity")
    warehouse_count = func.count(func.distinct(latest.c.warehouse_id)).label("warehouse_count")
    statement = (
        select(Product.id, Product.product_code, Product.name, total_quantity, warehouse_count)
        .outerjoin(latest, latest.c.product_id == Product.id)
        .where(Product.organization_id == organization_id)
        .group_by(Product.id, Product.product_code, Product.name)
    )
    if search:
        term = f"%{search.strip()}%"
        statement = statement.where(Product.product_code.ilike(term) | Product.name.ilike(term))
    if status == InventoryStatus.IN_STOCK:
        statement = statement.having(total_quantity > 0)
    elif status == InventoryStatus.OUT_OF_STOCK:
        statement = statement.having(total_quantity <= 0)
    sort_columns = {
        "code": Product.product_code,
        "name": Product.name,
        "quantity": total_quantity,
        "warehouses": warehouse_count,
    }
    order_column = sort_columns[sort]
    statement = statement.order_by(
        order_column.desc() if descending else order_column, Product.product_code
    )
    rows = db.execute(statement.offset(offset).limit(limit)).all()
    return [
        InventoryProductInsight(
            product_id=row[0],
            product_code=row[1],
            product_name=row[2],
            total_quantity=Decimal(str(row[3] or 0)),
            warehouse_count=int(row[4]),
            status=_inventory_status(Decimal(str(row[3] or 0))),
        )
        for row in rows
    ]
