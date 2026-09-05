import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.infrastructure.database.session import get_db
from app.models.inventory_snapshot import InventorySnapshot
from app.models.product import Product
from app.models.supplier import Supplier
from app.models.user import User
from app.models.warehouse import Warehouse
from app.schemas.master_data import (
    InventoryCreate,
    InventoryResponse,
    ProductCreate,
    ProductResponse,
    ProductUpdate,
    SupplierCreate,
    SupplierResponse,
    SupplierUpdate,
    WarehouseCreate,
    WarehouseResponse,
    WarehouseUpdate,
)
from app.services.master_data_service import (
    MasterDataConflict,
    create_inventory,
    create_product,
    create_supplier,
    create_warehouse,
    get_inventory,
    get_product,
    get_supplier,
    get_warehouse,
    list_inventory,
    list_products,
    list_suppliers,
    list_warehouses,
    update_product,
    update_supplier,
    update_warehouse,
)

router = APIRouter(tags=["master-data"])


def missing() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")


def pagination(offset: int, limit: int) -> tuple[int, int]:
    if offset < 0 or limit < 1 or limit > 100:
        raise HTTPException(
            status_code=422, detail="offset must be non-negative and limit must be 1-100"
        )
    return offset, limit


@router.get("/products", response_model=list[ProductResponse])
def products(
    offset: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Product]:
    return list_products(db, user.organization_id, *pagination(offset, limit))


@router.post("/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def product_create(
    payload: ProductCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> Product:
    try:
        return create_product(db, user.organization_id, payload.model_dump())
    except MasterDataConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/products/{product_id}", response_model=ProductResponse)
def product_get(
    product_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> Product:
    item = get_product(db, user.organization_id, product_id)
    if item is None:
        raise missing()
    return item


@router.patch("/products/{product_id}", response_model=ProductResponse)
def product_update(
    product_id: uuid.UUID,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Product:
    item = get_product(db, user.organization_id, product_id)
    if item is None:
        raise missing()
    try:
        return update_product(db, item, payload.model_dump(exclude_unset=True))
    except MasterDataConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/warehouses", response_model=list[WarehouseResponse])
def warehouses(
    offset: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Warehouse]:
    return list_warehouses(db, user.organization_id, *pagination(offset, limit))


@router.post("/warehouses", response_model=WarehouseResponse, status_code=status.HTTP_201_CREATED)
def warehouse_create(
    payload: WarehouseCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> Warehouse:
    try:
        return create_warehouse(db, user.organization_id, payload.model_dump())
    except MasterDataConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/warehouses/{warehouse_id}", response_model=WarehouseResponse)
def warehouse_get(
    warehouse_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> Warehouse:
    item = get_warehouse(db, user.organization_id, warehouse_id)
    if item is None:
        raise missing()
    return item


@router.patch("/warehouses/{warehouse_id}", response_model=WarehouseResponse)
def warehouse_update(
    warehouse_id: uuid.UUID,
    payload: WarehouseUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Warehouse:
    item = get_warehouse(db, user.organization_id, warehouse_id)
    if item is None:
        raise missing()
    try:
        return update_warehouse(db, item, payload.model_dump(exclude_unset=True))
    except MasterDataConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/suppliers", response_model=list[SupplierResponse])
def suppliers(
    offset: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Supplier]:
    return list_suppliers(db, user.organization_id, *pagination(offset, limit))


@router.post("/suppliers", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED)
def supplier_create(
    payload: SupplierCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> Supplier:
    try:
        return create_supplier(db, user.organization_id, payload.model_dump())
    except MasterDataConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/suppliers/{supplier_id}", response_model=SupplierResponse)
def supplier_get(
    supplier_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> Supplier:
    item = get_supplier(db, user.organization_id, supplier_id)
    if item is None:
        raise missing()
    return item


@router.patch("/suppliers/{supplier_id}", response_model=SupplierResponse)
def supplier_update(
    supplier_id: uuid.UUID,
    payload: SupplierUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Supplier:
    item = get_supplier(db, user.organization_id, supplier_id)
    if item is None:
        raise missing()
    try:
        return update_supplier(db, item, payload.model_dump(exclude_unset=True))
    except MasterDataConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/inventory", response_model=list[InventoryResponse])
def inventory(
    offset: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[InventorySnapshot]:
    return list_inventory(db, user.organization_id, *pagination(offset, limit))


@router.post("/inventory", response_model=InventoryResponse, status_code=status.HTTP_201_CREATED)
def inventory_create(
    payload: InventoryCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> InventorySnapshot:
    try:
        return create_inventory(db, user.organization_id, payload.model_dump())
    except MasterDataConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/inventory/{snapshot_id}", response_model=InventoryResponse)
def inventory_get(
    snapshot_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> InventorySnapshot:
    item = get_inventory(db, user.organization_id, snapshot_id)
    if item is None:
        raise missing()
    return item
