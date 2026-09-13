from collections.abc import Iterator
from datetime import date
from pathlib import PurePath

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.config import get_settings
from app.infrastructure.database.session import SessionLocal, get_db
from app.models.user import User
from app.schemas.analytics import TrendPeriod
from app.schemas.reports import (
    ExportFormat,
    InventoryReportResponse,
    ProductReportResponse,
    ReportQuery,
    ReportType,
    SalesReportResponse,
    WarehouseReportResponse,
)
from app.services.reporting_service import (
    inventory_report,
    product_report,
    sales_report,
    stream_csv_report,
    warehouse_report,
)

router = APIRouter(prefix="/reports", tags=["reports"])


def validate_date_range(date_from: date | None, date_to: date | None) -> None:
    if date_from is not None and date_to is not None and date_from > date_to:
        raise HTTPException(status_code=422, detail="date_from must not be after date_to")


def report_query(
    query: ReportQuery,
) -> tuple[date | None, date | None, str | None, str | None, TrendPeriod, int]:
    validate_date_range(query.date_from, query.date_to)
    return (
        query.date_from,
        query.date_to,
        query.product_code,
        query.warehouse_code,
        TrendPeriod(query.period),
        query.limit,
    )


@router.get("/sales", response_model=SalesReportResponse)
def sales(
    query: ReportQuery = Depends(),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SalesReportResponse:
    date_from, date_to, product_code, warehouse_code, period, limit = report_query(query)
    return sales_report(
        db,
        user.organization_id,
        date_from,
        date_to,
        product_code,
        warehouse_code,
        period,
        limit,
    )


@router.get("/products", response_model=ProductReportResponse)
def products(
    query: ReportQuery = Depends(),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ProductReportResponse:
    date_from, date_to, product_code, warehouse_code, _, limit = report_query(query)
    return product_report(
        db, user.organization_id, date_from, date_to, product_code, warehouse_code, limit
    )


@router.get("/inventory", response_model=InventoryReportResponse)
def inventory(
    query: ReportQuery = Depends(),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> InventoryReportResponse:
    date_from, date_to, product_code, warehouse_code, _, limit = report_query(query)
    return inventory_report(
        db, user.organization_id, date_from, date_to, product_code, warehouse_code, limit
    )


@router.get("/warehouses", response_model=WarehouseReportResponse)
def warehouses(
    query: ReportQuery = Depends(),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WarehouseReportResponse:
    date_from, date_to, product_code, warehouse_code, _, limit = report_query(query)
    return warehouse_report(
        db, user.organization_id, date_from, date_to, product_code, warehouse_code, limit
    )


@router.get("/{report_type}/export")
def export_report(
    report_type: ReportType,
    query: ReportQuery = Depends(),
    format: ExportFormat = Query(ExportFormat.CSV),
    user: User = Depends(get_current_user),
) -> StreamingResponse:
    if format != ExportFormat.CSV:
        raise HTTPException(status_code=422, detail="Only CSV export is supported")
    date_from, date_to, product_code, warehouse_code, period, limit = report_query(query)
    settings = get_settings()
    export_limit = (
        settings.report_export_max_rows
        if report_type in {ReportType.SALES, ReportType.INVENTORY}
        else limit
    )
    start = date_from.isoformat() if date_from else "all"
    end = date_to.isoformat() if date_to else "time"
    filename = PurePath(f"mosaic-{report_type.value}-report-{start}-{end}.csv").name

    def rows() -> Iterator[str]:
        with SessionLocal() as export_db:
            yield from stream_csv_report(
                export_db,
                user.organization_id,
                report_type,
                date_from,
                date_to,
                product_code,
                warehouse_code,
                period,
                export_limit,
            )

    return StreamingResponse(
        rows(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
