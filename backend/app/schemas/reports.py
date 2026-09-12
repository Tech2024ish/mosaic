from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.analytics import (
    AnalyticsQuery,
    InventoryAnalyticsResponse,
    SalesAnalyticsResponse,
    SalesTrendItem,
    TopProductItem,
    WarehousePerformanceItem,
)


class ReportType(StrEnum):
    SALES = "sales"
    PRODUCTS = "products"
    INVENTORY = "inventory"
    WAREHOUSES = "warehouses"


class ExportFormat(StrEnum):
    CSV = "csv"


class ReportQuery(AnalyticsQuery):
    period: str = Field(default="month", pattern="^(day|week|month)$")
    limit: int = Field(default=100, ge=1, le=100)


class ReportPeriod(BaseModel):
    date_from: date | None
    date_to: date | None


class SalesReportResponse(BaseModel):
    report_type: Literal["sales"] = "sales"
    period: ReportPeriod
    summary: SalesAnalyticsResponse
    trend: list[SalesTrendItem]
    top_products: list[TopProductItem]
    warehouse_performance: list[WarehousePerformanceItem]


class ProductReportResponse(BaseModel):
    report_type: Literal["products"] = "products"
    period: ReportPeriod
    items: list[TopProductItem]


class InventoryReportItem(BaseModel):
    product_code: str
    product_name: str | None
    warehouse_code: str
    warehouse_name: str | None
    snapshot_date: date
    quantity_on_hand: Decimal
    unit_cost: Decimal | None


class InventoryReportResponse(BaseModel):
    report_type: Literal["inventory"] = "inventory"
    period: ReportPeriod
    summary: InventoryAnalyticsResponse
    items: list[InventoryReportItem]


class WarehouseReportResponse(BaseModel):
    report_type: Literal["warehouses"] = "warehouses"
    period: ReportPeriod
    items: list[WarehousePerformanceItem]
