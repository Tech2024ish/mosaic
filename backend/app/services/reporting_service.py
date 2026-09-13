import csv
import io
import uuid
from collections.abc import Iterator
from datetime import date
from typing import Any

from sqlalchemy import Select, and_, func, select
from sqlalchemy.orm import Session

from app.models.inventory_snapshot import InventorySnapshot
from app.models.product import Product
from app.models.sales_history import SalesHistory
from app.models.warehouse import Warehouse
from app.schemas.analytics import (
    AnalyticsQuery,
    InventoryAnalyticsResponse,
    TrendPeriod,
)
from app.schemas.reports import (
    InventoryReportItem,
    InventoryReportResponse,
    ProductReportResponse,
    ReportPeriod,
    ReportType,
    SalesReportResponse,
    WarehouseReportResponse,
)
from app.services.analytics_service import (
    _decimal,
    _latest_inventory_query,
    inventory_analytics,
    sales_analytics,
    sales_trend,
    top_products,
    warehouse_performance,
)


def report_period(date_from: date | None, date_to: date | None) -> ReportPeriod:
    return ReportPeriod(date_from=date_from, date_to=date_to)


def _query_values(query: AnalyticsQuery) -> tuple[date | None, date | None, str | None, str | None]:
    return query.date_from, query.date_to, query.product_code, query.warehouse_code


def sales_report(
    db: Session,
    organization_id: uuid.UUID,
    date_from: date | None,
    date_to: date | None,
    product_code: str | None,
    warehouse_code: str | None,
    period: TrendPeriod,
    limit: int,
) -> SalesReportResponse:
    summary = sales_analytics(db, organization_id, date_from, date_to, product_code, warehouse_code)
    trend = sales_trend(
        db, organization_id, period, date_from, date_to, product_code, warehouse_code
    )
    return SalesReportResponse(
        period=report_period(date_from, date_to),
        summary=summary,
        trend=trend.data,
        top_products=top_products(
            db, organization_id, limit, date_from, date_to, product_code, warehouse_code
        ).items,
        warehouse_performance=warehouse_performance(
            db, organization_id, limit, date_from, date_to, product_code, warehouse_code
        ).items,
    )


def product_report(
    db: Session,
    organization_id: uuid.UUID,
    date_from: date | None,
    date_to: date | None,
    product_code: str | None,
    warehouse_code: str | None,
    limit: int,
) -> ProductReportResponse:
    return ProductReportResponse(
        period=report_period(date_from, date_to),
        items=top_products(
            db, organization_id, limit, date_from, date_to, product_code, warehouse_code
        ).items,
    )


def warehouse_report(
    db: Session,
    organization_id: uuid.UUID,
    date_from: date | None,
    date_to: date | None,
    product_code: str | None,
    warehouse_code: str | None,
    limit: int,
) -> WarehouseReportResponse:
    return WarehouseReportResponse(
        period=report_period(date_from, date_to),
        items=warehouse_performance(
            db, organization_id, limit, date_from, date_to, product_code, warehouse_code
        ).items,
    )


def inventory_rows(
    db: Session,
    organization_id: uuid.UUID,
    date_from: date | None,
    date_to: date | None,
    product_code: str | None,
    warehouse_code: str | None,
    limit: int | None,
) -> Select[Any]:
    if date_from is None and date_to is None:
        latest = _latest_inventory_query(organization_id).subquery()
        statement: Select[Any] = (
            select(
                Product.product_code,
                Product.name,
                Warehouse.warehouse_code,
                Warehouse.name,
                latest.c.snapshot_date,
                latest.c.quantity_on_hand,
                latest.c.unit_cost,
            )
            .select_from(latest)
            .join(
                Product,
                and_(
                    Product.id == latest.c.product_id,
                    Product.organization_id == organization_id,
                ),
            )
            .join(
                Warehouse,
                and_(
                    Warehouse.id == latest.c.warehouse_id,
                    Warehouse.organization_id == organization_id,
                ),
            )
            .order_by(
                latest.c.snapshot_date.desc(),
                Product.product_code,
                Warehouse.warehouse_code,
                latest.c.id,
            )
        )
        if product_code:
            statement = statement.where(Product.product_code == product_code.strip().upper())
        if warehouse_code:
            statement = statement.where(Warehouse.warehouse_code == warehouse_code.strip().upper())
        if limit is not None:
            statement = statement.limit(limit)
        return statement

    historical_statement: Select[Any] = (
        select(
            Product.product_code,
            Product.name,
            Warehouse.warehouse_code,
            Warehouse.name,
            InventorySnapshot.snapshot_date,
            InventorySnapshot.quantity_on_hand,
            InventorySnapshot.unit_cost,
        )
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
        .order_by(
            InventorySnapshot.snapshot_date.desc(),
            Product.product_code,
            Warehouse.warehouse_code,
            InventorySnapshot.id,
        )
    )
    if date_from is not None:
        historical_statement = historical_statement.where(
            InventorySnapshot.snapshot_date >= date_from
        )
    if date_to is not None:
        historical_statement = historical_statement.where(
            InventorySnapshot.snapshot_date <= date_to
        )
    if product_code:
        historical_statement = historical_statement.where(
            Product.product_code == product_code.strip().upper()
        )
    if warehouse_code:
        historical_statement = historical_statement.where(
            Warehouse.warehouse_code == warehouse_code.strip().upper()
        )
    if limit is not None:
        historical_statement = historical_statement.limit(limit)
    return historical_statement


def report_inventory_summary(
    db: Session,
    organization_id: uuid.UUID,
    date_from: date | None,
    date_to: date | None,
    product_code: str | None,
    warehouse_code: str | None,
) -> InventoryAnalyticsResponse:
    if date_from is not None or date_to is not None:
        return inventory_analytics(
            db, organization_id, date_from, date_to, product_code, warehouse_code
        )
    latest = _latest_inventory_query(organization_id).subquery()
    statement = (
        select(
            func.count(latest.c.id),
            func.coalesce(func.sum(latest.c.quantity_on_hand), 0),
        )
        .select_from(latest)
        .join(
            Product,
            and_(Product.id == latest.c.product_id, Product.organization_id == organization_id),
        )
        .join(
            Warehouse,
            and_(
                Warehouse.id == latest.c.warehouse_id, Warehouse.organization_id == organization_id
            ),
        )
    )
    if product_code:
        statement = statement.where(Product.product_code == product_code.strip().upper())
    if warehouse_code:
        statement = statement.where(Warehouse.warehouse_code == warehouse_code.strip().upper())
    row = db.execute(statement).one()
    return InventoryAnalyticsResponse(
        inventory_record_count=int(row[0]), total_quantity=_decimal(row[1])
    )


def inventory_report(
    db: Session,
    organization_id: uuid.UUID,
    date_from: date | None,
    date_to: date | None,
    product_code: str | None,
    warehouse_code: str | None,
    limit: int,
) -> InventoryReportResponse:
    summary: InventoryAnalyticsResponse = report_inventory_summary(
        db, organization_id, date_from, date_to, product_code, warehouse_code
    )
    rows = db.execute(
        inventory_rows(db, organization_id, date_from, date_to, product_code, warehouse_code, limit)
    ).all()
    return InventoryReportResponse(
        period=report_period(date_from, date_to),
        summary=summary,
        items=[
            InventoryReportItem(
                product_code=row[0],
                product_name=row[1],
                warehouse_code=row[2],
                warehouse_name=row[3],
                snapshot_date=row[4],
                quantity_on_hand=_decimal(row[5]),
                unit_cost=_decimal(row[6]) if row[6] is not None else None,
            )
            for row in rows
        ],
    )


def _csv_line(values: tuple[object, ...]) -> str:
    output = io.StringIO(newline="")
    csv.writer(output, lineterminator="\n").writerow(values)
    return output.getvalue()


def stream_csv_report(
    db: Session,
    organization_id: uuid.UUID,
    report_type: ReportType,
    date_from: date | None,
    date_to: date | None,
    product_code: str | None,
    warehouse_code: str | None,
    period: TrendPeriod,
    limit: int,
) -> Iterator[str]:
    if report_type == ReportType.SALES:
        yield _csv_line(
            ("sale_date", "product_code", "warehouse_code", "quantity", "unit_price", "revenue")
        )
        revenue = SalesHistory.quantity * SalesHistory.unit_price
        statement = (
            select(
                SalesHistory.sale_date,
                SalesHistory.product_code,
                SalesHistory.warehouse_code,
                SalesHistory.quantity,
                SalesHistory.unit_price,
                revenue,
            )
            .where(SalesHistory.organization_id == organization_id)
            .order_by(SalesHistory.sale_date, SalesHistory.id)
        )
        statement = _apply_sales_filters(
            statement, date_from, date_to, product_code, warehouse_code
        )
        statement = statement.limit(limit)
        for row in db.execute(statement.execution_options(stream_results=True)).yield_per(1000):
            yield _csv_line(tuple(row))
        return

    if report_type == ReportType.INVENTORY:
        yield _csv_line(
            (
                "product_code",
                "product_name",
                "warehouse_code",
                "warehouse_name",
                "snapshot_date",
                "quantity_on_hand",
                "unit_cost",
            )
        )
        for row in db.execute(
            inventory_rows(
                db,
                organization_id,
                date_from,
                date_to,
                product_code,
                warehouse_code,
                limit,
            ).execution_options(stream_results=True)
        ).yield_per(1000):
            yield _csv_line(tuple(row))
        return

    if report_type == ReportType.PRODUCTS:
        product_result = product_report(
            db, organization_id, date_from, date_to, product_code, warehouse_code, limit
        )
        yield _csv_line(
            ("rank", "product_code", "product_name", "sales_count", "quantity_sold", "revenue")
        )
        for product_item in product_result.items:
            yield _csv_line(
                (
                    product_item.rank,
                    product_item.product_code,
                    product_item.product_name or "",
                    product_item.sales_count,
                    product_item.quantity_sold,
                    product_item.revenue,
                )
            )
        return

    warehouse_result = warehouse_report(
        db, organization_id, date_from, date_to, product_code, warehouse_code, limit
    )
    yield _csv_line(
        ("rank", "warehouse_code", "warehouse_name", "sales_count", "quantity_sold", "revenue")
    )
    for warehouse_item in warehouse_result.items:
        yield _csv_line(
            (
                warehouse_item.rank,
                warehouse_item.warehouse_code,
                warehouse_item.warehouse_name or "",
                warehouse_item.sales_count,
                warehouse_item.quantity_sold,
                warehouse_item.revenue,
            )
        )


def _apply_sales_filters(
    statement: Select[Any],
    date_from: date | None,
    date_to: date | None,
    product_code: str | None,
    warehouse_code: str | None,
) -> Select[Any]:
    if date_from is not None:
        statement = statement.where(SalesHistory.sale_date >= date_from)
    if date_to is not None:
        statement = statement.where(SalesHistory.sale_date <= date_to)
    if product_code:
        statement = statement.where(SalesHistory.product_code == product_code.strip().upper())
    if warehouse_code:
        statement = statement.where(SalesHistory.warehouse_code == warehouse_code.strip().upper())
    return statement
