import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Select, and_, func, select
from sqlalchemy.orm import Session

from app.models.inventory_snapshot import InventorySnapshot
from app.models.product import Product
from app.models.sales_history import SalesHistory
from app.models.supplier import Supplier
from app.models.warehouse import Warehouse
from app.schemas.analytics import (
    AnalyticsSummaryResponse,
    InventoryAnalyticsResponse,
    SalesAnalyticsResponse,
    SalesTrendItem,
    SalesTrendResponse,
    TopProductItem,
    TopProductsResponse,
    TrendPeriod,
    WarehousePerformanceItem,
    WarehousePerformanceResponse,
)


def _decimal(value: Any) -> Decimal:
    return Decimal(str(value if value is not None else "0"))


def _sales_statement(
    organization_id: uuid.UUID,
    date_from: date | None,
    date_to: date | None,
    product_code: str | None,
    warehouse_code: str | None,
) -> Select[Any]:
    statement: Select[Any] = select(SalesHistory).where(
        SalesHistory.organization_id == organization_id
    )
    if date_from is not None:
        statement = statement.where(SalesHistory.sale_date >= date_from)
    if date_to is not None:
        statement = statement.where(SalesHistory.sale_date <= date_to)
    if product_code:
        statement = statement.where(SalesHistory.product_code == product_code.strip().upper())
    if warehouse_code:
        statement = statement.where(SalesHistory.warehouse_code == warehouse_code.strip().upper())
    return statement


def sales_analytics(
    db: Session,
    organization_id: uuid.UUID,
    date_from: date | None = None,
    date_to: date | None = None,
    product_code: str | None = None,
    warehouse_code: str | None = None,
) -> SalesAnalyticsResponse:
    filtered = _sales_statement(
        organization_id, date_from, date_to, product_code, warehouse_code
    ).subquery()
    revenue = filtered.c.quantity * filtered.c.unit_price
    row = db.execute(
        select(
            func.count(filtered.c.id),
            func.coalesce(func.sum(filtered.c.quantity), 0),
            func.coalesce(func.sum(filtered.c.quantity * filtered.c.unit_price), 0),
            func.coalesce(func.avg(revenue), 0),
        )
    ).one()
    return SalesAnalyticsResponse(
        sales_count=int(row[0]),
        total_quantity=_decimal(row[1]),
        total_revenue=_decimal(row[2]),
        average_sale_value=_decimal(row[3]),
    )


def _latest_inventory_query(organization_id: uuid.UUID) -> Select[Any]:
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
        select(InventorySnapshot)
        .join(
            latest_dates,
            and_(
                InventorySnapshot.product_id == latest_dates.c.product_id,
                InventorySnapshot.warehouse_id == latest_dates.c.warehouse_id,
                InventorySnapshot.snapshot_date == latest_dates.c.latest_date,
            ),
        )
        .where(InventorySnapshot.organization_id == organization_id)
    )


def current_inventory_totals(db: Session, organization_id: uuid.UUID) -> tuple[Decimal, int]:
    latest = _latest_inventory_query(organization_id).subquery()
    row = db.execute(
        select(
            func.coalesce(func.sum(latest.c.quantity_on_hand), 0),
            func.count(latest.c.id),
        )
    ).one()
    return _decimal(row[0]), int(row[1])


def analytics_summary(
    db: Session,
    organization_id: uuid.UUID,
    date_from: date | None = None,
    date_to: date | None = None,
    product_code: str | None = None,
    warehouse_code: str | None = None,
) -> AnalyticsSummaryResponse:
    sales = sales_analytics(db, organization_id, date_from, date_to, product_code, warehouse_code)
    inventory_quantity, inventory_records = current_inventory_totals(db, organization_id)
    return AnalyticsSummaryResponse(
        sales_count=sales.sales_count,
        total_quantity=sales.total_quantity,
        total_revenue=sales.total_revenue,
        average_sale_value=sales.average_sale_value,
        product_count=int(
            db.scalar(
                select(func.count(Product.id)).where(Product.organization_id == organization_id)
            )
            or 0
        ),
        warehouse_count=int(
            db.scalar(
                select(func.count(Warehouse.id)).where(Warehouse.organization_id == organization_id)
            )
            or 0
        ),
        supplier_count=int(
            db.scalar(
                select(func.count(Supplier.id)).where(Supplier.organization_id == organization_id)
            )
            or 0
        ),
        inventory_quantity=inventory_quantity,
        inventory_record_count=inventory_records,
    )


def sales_trend(
    db: Session,
    organization_id: uuid.UUID,
    period: TrendPeriod,
    date_from: date | None = None,
    date_to: date | None = None,
    product_code: str | None = None,
    warehouse_code: str | None = None,
) -> SalesTrendResponse:
    if db.get_bind().dialect.name == "sqlite":
        format_string = {
            TrendPeriod.DAY: "%Y-%m-%d",
            TrendPeriod.WEEK: "%Y-W%W",
            TrendPeriod.MONTH: "%Y-%m",
        }[period]
        period_expression = func.strftime(format_string, SalesHistory.sale_date).label("period")
    else:
        period_expression = func.date_trunc(period.value, SalesHistory.sale_date).label("period")
    revenue = SalesHistory.quantity * SalesHistory.unit_price
    statement = _sales_statement(
        organization_id, date_from, date_to, product_code, warehouse_code
    ).with_only_columns(
        period_expression,
        func.count(SalesHistory.id),
        func.coalesce(func.sum(SalesHistory.quantity), 0),
        func.coalesce(func.sum(revenue), 0),
    )
    rows = db.execute(statement.group_by(period_expression).order_by(period_expression)).all()
    return SalesTrendResponse(
        period=period,
        data=[
            SalesTrendItem(
                period=_format_period(row[0], period),
                sales_count=int(row[1]),
                total_quantity=_decimal(row[2]),
                revenue=_decimal(row[3]),
            )
            for row in rows
        ],
    )


def _format_period(value: Any, period: TrendPeriod) -> str:
    if isinstance(value, datetime):
        if period == TrendPeriod.MONTH:
            return value.strftime("%Y-%m")
        return value.strftime("%Y-%m-%d")
    return str(value)


def top_products(
    db: Session,
    organization_id: uuid.UUID,
    limit: int,
    date_from: date | None = None,
    date_to: date | None = None,
    product_code: str | None = None,
    warehouse_code: str | None = None,
) -> TopProductsResponse:
    revenue = SalesHistory.quantity * SalesHistory.unit_price
    statement = (
        _sales_statement(organization_id, date_from, date_to, product_code, warehouse_code)
        .join(
            Product,
            and_(
                Product.organization_id == organization_id,
                Product.product_code == SalesHistory.product_code,
            ),
            isouter=True,
        )
        .with_only_columns(
            SalesHistory.product_code,
            func.max(Product.name),
            func.count(SalesHistory.id),
            func.coalesce(func.sum(SalesHistory.quantity), 0),
            func.coalesce(func.sum(revenue), 0),
        )
        .group_by(SalesHistory.product_code)
        .order_by(func.sum(revenue).desc(), SalesHistory.product_code)
        .limit(limit)
    )
    rows = db.execute(statement).all()
    return TopProductsResponse(
        items=[
            TopProductItem(
                rank=index,
                product_code=row[0],
                product_name=row[1],
                sales_count=int(row[2]),
                quantity_sold=_decimal(row[3]),
                revenue=_decimal(row[4]),
            )
            for index, row in enumerate(rows, start=1)
        ]
    )


def warehouse_performance(
    db: Session,
    organization_id: uuid.UUID,
    limit: int,
    date_from: date | None = None,
    date_to: date | None = None,
    product_code: str | None = None,
    warehouse_code: str | None = None,
) -> WarehousePerformanceResponse:
    revenue = SalesHistory.quantity * SalesHistory.unit_price
    statement = (
        _sales_statement(organization_id, date_from, date_to, product_code, warehouse_code)
        .join(
            Warehouse,
            and_(
                Warehouse.organization_id == organization_id,
                Warehouse.warehouse_code == SalesHistory.warehouse_code,
            ),
            isouter=True,
        )
        .with_only_columns(
            SalesHistory.warehouse_code,
            func.max(Warehouse.name),
            func.count(SalesHistory.id),
            func.coalesce(func.sum(SalesHistory.quantity), 0),
            func.coalesce(func.sum(revenue), 0),
        )
        .group_by(SalesHistory.warehouse_code)
        .order_by(func.sum(revenue).desc(), SalesHistory.warehouse_code)
        .limit(limit)
    )
    rows = db.execute(statement).all()
    return WarehousePerformanceResponse(
        items=[
            WarehousePerformanceItem(
                rank=index,
                warehouse_code=row[0],
                warehouse_name=row[1],
                sales_count=int(row[2]),
                quantity_sold=_decimal(row[3]),
                revenue=_decimal(row[4]),
            )
            for index, row in enumerate(rows, start=1)
        ]
    )


def inventory_analytics(
    db: Session,
    organization_id: uuid.UUID,
    date_from: date | None = None,
    date_to: date | None = None,
    product_code: str | None = None,
    warehouse_code: str | None = None,
) -> InventoryAnalyticsResponse:
    statement = (
        select(
            func.count(InventorySnapshot.id),
            func.coalesce(func.sum(InventorySnapshot.quantity_on_hand), 0),
        )
        .select_from(InventorySnapshot)
        .join(
            Product,
            and_(
                Product.id == InventorySnapshot.product_id,
                Product.organization_id == organization_id,
            ),
        )
        .join(
            Warehouse,
            and_(
                Warehouse.id == InventorySnapshot.warehouse_id,
                Warehouse.organization_id == organization_id,
            ),
        )
        .where(InventorySnapshot.organization_id == organization_id)
    )
    if date_from is not None:
        statement = statement.where(InventorySnapshot.snapshot_date >= date_from)
    if date_to is not None:
        statement = statement.where(InventorySnapshot.snapshot_date <= date_to)
    if product_code:
        statement = statement.where(Product.product_code == product_code.strip().upper())
    if warehouse_code:
        statement = statement.where(Warehouse.warehouse_code == warehouse_code.strip().upper())
    row = db.execute(statement).one()
    return InventoryAnalyticsResponse(
        inventory_record_count=int(row[0]), total_quantity=_decimal(row[1])
    )
