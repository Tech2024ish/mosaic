import uuid
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from app.schemas.insights import (
    ComparisonMetric,
    ComparisonResponse,
    InsightCategory,
    InsightPeriod,
    InsightRecord,
    InsightsOverviewResponse,
)
from app.services.analytics_service import sales_analytics, top_products, warehouse_performance
from app.services.master_data_service import inventory_summary

TWO_PLACES = Decimal("0.01")


def _period(date_from: date | None, date_to: date | None) -> InsightPeriod:
    return InsightPeriod(date_from=date_from, date_to=date_to)


def _money(value: Decimal) -> str:
    return f"{value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP):,.2f}"


def _comparison_category(change: Decimal) -> InsightCategory:
    if change > 0:
        return InsightCategory.POSITIVE
    if change < 0:
        return InsightCategory.NEGATIVE
    return InsightCategory.NEUTRAL


def _comparison_metric(name: str, current: Decimal, previous: Decimal) -> ComparisonMetric:
    change = current - previous
    change_percent = None
    if previous != 0:
        change_percent = (change / abs(previous) * Decimal("100")).quantize(
            TWO_PLACES, rounding=ROUND_HALF_UP
        )
    return ComparisonMetric(
        name=name,
        current_value=current,
        previous_value=previous,
        change=change,
        change_percent=change_percent,
        category=_comparison_category(change),
    )


def _comparison_insight(metric: ComparisonMetric) -> InsightRecord:
    direction = (
        "increased" if metric.change > 0 else "decreased" if metric.change < 0 else "did not change"
    )
    if metric.change_percent is None:
        description = f"{metric.name.replace('_', ' ').capitalize()} {direction}; the previous period had no recorded value."
    else:
        description = (
            f"{metric.name.replace('_', ' ').capitalize()} {direction} by "
            f"{abs(metric.change_percent):,.2f}% compared with the previous period."
        )
    return InsightRecord(
        code=f"comparison_{metric.name}",
        category=metric.category,
        title=f"{metric.name.replace('_', ' ').capitalize()} comparison",
        description=description,
        metric=metric.change_percent,
        metric_label="change_percent",
    )


def insights_overview(
    db: Session,
    organization_id: uuid.UUID,
    date_from: date | None,
    date_to: date | None,
    product_code: str | None,
    warehouse_code: str | None,
    limit: int,
) -> InsightsOverviewResponse:
    summary = sales_analytics(db, organization_id, date_from, date_to, product_code, warehouse_code)
    products = top_products(
        db,
        organization_id,
        limit,
        date_from,
        date_to,
        product_code,
        warehouse_code,
    ).items
    warehouses = warehouse_performance(
        db,
        organization_id,
        limit,
        date_from,
        date_to,
        product_code,
        warehouse_code,
    ).items
    inventory = inventory_summary(db, organization_id)
    insights: list[InsightRecord] = []
    if summary.sales_count == 0:
        insights.append(
            InsightRecord(
                code="no_sales_activity",
                category=InsightCategory.INFORMATIONAL,
                title="No sales activity recorded",
                description="No sales records match the selected period and filters.",
            )
        )
    elif products and summary.total_revenue > 0:
        top = products[0]
        share = (top.revenue / summary.total_revenue * Decimal("100")).quantize(
            TWO_PLACES, rounding=ROUND_HALF_UP
        )
        insights.append(
            InsightRecord(
                code="revenue_concentration",
                category=InsightCategory.INFORMATIONAL,
                title="Leading product revenue contribution",
                description=(
                    f"{top.product_name or top.product_code} generated {share:,.2f}% of "
                    "recorded revenue in the selected period."
                ),
                metric=share,
                metric_label="revenue_share_percent",
            )
        )
    if warehouses:
        leading = warehouses[0]
        insights.append(
            InsightRecord(
                code="leading_warehouse",
                category=InsightCategory.INFORMATIONAL,
                title="Leading warehouse activity",
                description=(
                    f"{leading.warehouse_name or leading.warehouse_code} recorded the "
                    f"highest revenue in the selected period: {_money(leading.revenue)}."
                ),
                metric=leading.revenue,
                metric_label="revenue",
            )
        )
    if inventory.out_of_stock_products > 0:
        insights.append(
            InsightRecord(
                code="inventory_attention",
                category=InsightCategory.ATTENTION,
                title="Products have no available inventory",
                description=(
                    f"{inventory.out_of_stock_products} product(s) currently have no "
                    "available inventory in the latest recorded position."
                ),
                metric=Decimal(inventory.out_of_stock_products),
                metric_label="out_of_stock_products",
            )
        )
    return InsightsOverviewResponse(
        period=_period(date_from, date_to),
        summary=summary,
        top_products=products,
        warehouse_performance=warehouses,
        inventory=inventory,
        insights=insights,
    )


def period_comparison(
    db: Session,
    organization_id: uuid.UUID,
    date_from: date,
    date_to: date,
    product_code: str | None,
    warehouse_code: str | None,
) -> ComparisonResponse:
    duration = (date_to - date_from).days + 1
    previous_to = date_from - timedelta(days=1)
    previous_from = previous_to - timedelta(days=duration - 1)
    current = sales_analytics(db, organization_id, date_from, date_to, product_code, warehouse_code)
    previous = sales_analytics(
        db, organization_id, previous_from, previous_to, product_code, warehouse_code
    )
    metrics = [
        _comparison_metric("revenue", current.total_revenue, previous.total_revenue),
        _comparison_metric(
            "transactions", Decimal(current.sales_count), Decimal(previous.sales_count)
        ),
        _comparison_metric("quantity_sold", current.total_quantity, previous.total_quantity),
        _comparison_metric(
            "average_sale_value", current.average_sale_value, previous.average_sale_value
        ),
    ]
    return ComparisonResponse(
        current_period=_period(date_from, date_to),
        previous_period=_period(previous_from, previous_to),
        metrics=metrics,
        insights=[_comparison_insight(metric) for metric in metrics],
    )
