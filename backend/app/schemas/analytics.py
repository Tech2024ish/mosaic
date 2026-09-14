from datetime import date
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field


class TrendPeriod(StrEnum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


class SalesGroupBy(StrEnum):
    DATE = "date"
    PRODUCT = "product"
    WAREHOUSE = "warehouse"


class AnalyticsQuery(BaseModel):
    date_from: date | None = None
    date_to: date | None = None
    product_code: str | None = Field(default=None, max_length=200)
    warehouse_code: str | None = Field(default=None, max_length=200)


class SalesAnalyticsQuery(AnalyticsQuery):
    group_by: SalesGroupBy | None = None
    period: TrendPeriod = TrendPeriod.DAY
    limit: int = Field(default=100, ge=1, le=100)


class TrendQuery(AnalyticsQuery):
    period: TrendPeriod = TrendPeriod.MONTH


class TopItemsQuery(AnalyticsQuery):
    limit: int = Field(default=10, ge=1, le=100)


class AnalyticsSummaryResponse(BaseModel):
    sales_count: int
    total_quantity: Decimal
    total_revenue: Decimal
    average_sale_value: Decimal
    product_count: int
    warehouse_count: int
    supplier_count: int
    inventory_quantity: Decimal
    inventory_record_count: int


class SalesAnalyticsResponse(BaseModel):
    sales_count: int
    total_quantity: Decimal
    total_revenue: Decimal
    average_sale_value: Decimal
    groups: list["SalesAnalyticsGroup"] = Field(default_factory=list)


class SalesAnalyticsGroup(BaseModel):
    key: str
    label: str | None
    sales_count: int
    total_quantity: Decimal
    total_revenue: Decimal
    average_sale_value: Decimal


class SalesTrendItem(BaseModel):
    period: str
    sales_count: int
    total_quantity: Decimal
    revenue: Decimal


class SalesTrendResponse(BaseModel):
    period: TrendPeriod
    data: list[SalesTrendItem]


class TopProductItem(BaseModel):
    rank: int
    product_code: str
    product_name: str | None
    sales_count: int
    quantity_sold: Decimal
    revenue: Decimal


class TopProductsResponse(BaseModel):
    items: list[TopProductItem]


class WarehousePerformanceItem(BaseModel):
    rank: int
    warehouse_code: str
    warehouse_name: str | None
    sales_count: int
    quantity_sold: Decimal
    revenue: Decimal


class WarehousePerformanceResponse(BaseModel):
    items: list[WarehousePerformanceItem]


class InventoryAnalyticsResponse(BaseModel):
    inventory_record_count: int
    total_quantity: Decimal
