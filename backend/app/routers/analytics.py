from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.infrastructure.database.session import get_db
from app.models.user import User
from app.schemas.analytics import (
    AnalyticsQuery,
    AnalyticsSummaryResponse,
    InventoryAnalyticsResponse,
    SalesAnalyticsResponse,
    SalesTrendResponse,
    TopItemsQuery,
    TopProductsResponse,
    TrendQuery,
    WarehousePerformanceResponse,
)
from app.services.analytics_service import (
    analytics_summary,
    inventory_analytics,
    sales_analytics,
    sales_trend,
    top_products,
    warehouse_performance,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


def validate_date_range(date_from: date | None, date_to: date | None) -> None:
    if date_from is not None and date_to is not None and date_from > date_to:
        raise HTTPException(status_code=422, detail="date_from must not be after date_to")


@router.get("/summary", response_model=AnalyticsSummaryResponse)
def summary(
    query: AnalyticsQuery = Depends(),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AnalyticsSummaryResponse:
    validate_date_range(query.date_from, query.date_to)
    return analytics_summary(
        db,
        user.organization_id,
        query.date_from,
        query.date_to,
        query.product_code,
        query.warehouse_code,
    )


@router.get("/sales", response_model=SalesAnalyticsResponse)
def sales(
    query: AnalyticsQuery = Depends(),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SalesAnalyticsResponse:
    validate_date_range(query.date_from, query.date_to)
    return sales_analytics(
        db,
        user.organization_id,
        query.date_from,
        query.date_to,
        query.product_code,
        query.warehouse_code,
    )


@router.get("/sales/trend", response_model=SalesTrendResponse)
def trend(
    query: TrendQuery = Depends(),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SalesTrendResponse:
    validate_date_range(query.date_from, query.date_to)
    return sales_trend(
        db,
        user.organization_id,
        query.period,
        query.date_from,
        query.date_to,
        query.product_code,
        query.warehouse_code,
    )


@router.get("/products/top", response_model=TopProductsResponse)
def products_top(
    query: TopItemsQuery = Depends(),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TopProductsResponse:
    validate_date_range(query.date_from, query.date_to)
    return top_products(
        db,
        user.organization_id,
        query.limit,
        query.date_from,
        query.date_to,
        query.product_code,
        query.warehouse_code,
    )


@router.get("/warehouses/performance", response_model=WarehousePerformanceResponse)
def warehouses_performance(
    query: TopItemsQuery = Depends(),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WarehousePerformanceResponse:
    validate_date_range(query.date_from, query.date_to)
    return warehouse_performance(
        db,
        user.organization_id,
        query.limit,
        query.date_from,
        query.date_to,
        query.product_code,
        query.warehouse_code,
    )


@router.get("/inventory", response_model=InventoryAnalyticsResponse)
def inventory(
    query: AnalyticsQuery = Depends(),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> InventoryAnalyticsResponse:
    validate_date_range(query.date_from, query.date_to)
    return inventory_analytics(
        db,
        user.organization_id,
        query.date_from,
        query.date_to,
        query.product_code,
        query.warehouse_code,
    )
