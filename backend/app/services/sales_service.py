import uuid
from datetime import date

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.sales_history import SalesHistory


def list_sales(
    db: Session,
    organization_id: uuid.UUID,
    offset: int,
    limit: int,
    product_code: str | None = None,
    warehouse_code: str | None = None,
    sale_date_from: date | None = None,
    sale_date_to: date | None = None,
    sort: str = "sale_date",
    descending: bool = True,
) -> list[SalesHistory]:
    sort_columns = {
        "sale_date": SalesHistory.sale_date,
        "created_at": SalesHistory.created_at,
        "quantity": SalesHistory.quantity,
        "unit_price": SalesHistory.unit_price,
    }
    column = sort_columns[sort]
    statement: Select[tuple[SalesHistory]] = select(SalesHistory).where(
        SalesHistory.organization_id == organization_id
    )
    if product_code:
        statement = statement.where(SalesHistory.product_code == product_code.strip().upper())
    if warehouse_code:
        statement = statement.where(SalesHistory.warehouse_code == warehouse_code.strip().upper())
    if sale_date_from is not None:
        statement = statement.where(SalesHistory.sale_date >= sale_date_from)
    if sale_date_to is not None:
        statement = statement.where(SalesHistory.sale_date <= sale_date_to)
    statement = statement.order_by(column.desc() if descending else column, SalesHistory.id)
    return list(db.scalars(statement.offset(offset).limit(limit)))


def get_sale(db: Session, organization_id: uuid.UUID, sale_id: uuid.UUID) -> SalesHistory | None:
    return db.scalar(
        select(SalesHistory).where(
            SalesHistory.id == sale_id, SalesHistory.organization_id == organization_id
        )
    )
