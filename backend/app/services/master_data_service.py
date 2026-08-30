import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.inventory_snapshot import InventorySnapshot
from app.models.product import Product
from app.models.supplier import Supplier
from app.models.warehouse import Warehouse


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


def list_products(db: Session, organization_id: uuid.UUID) -> list[Product]:
    return list(
        db.scalars(
            select(Product)
            .where(Product.organization_id == organization_id)
            .order_by(Product.product_code)
        )
    )


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


def list_warehouses(db: Session, organization_id: uuid.UUID) -> list[Warehouse]:
    return list(
        db.scalars(
            select(Warehouse)
            .where(Warehouse.organization_id == organization_id)
            .order_by(Warehouse.warehouse_code)
        )
    )


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


def list_suppliers(db: Session, organization_id: uuid.UUID) -> list[Supplier]:
    return list(
        db.scalars(
            select(Supplier)
            .where(Supplier.organization_id == organization_id)
            .order_by(Supplier.supplier_code)
        )
    )


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


def list_inventory(db: Session, organization_id: uuid.UUID) -> list[InventorySnapshot]:
    return list(
        db.scalars(
            select(InventorySnapshot)
            .where(InventorySnapshot.organization_id == organization_id)
            .order_by(InventorySnapshot.snapshot_date.desc(), InventorySnapshot.id)
        )
    )


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
