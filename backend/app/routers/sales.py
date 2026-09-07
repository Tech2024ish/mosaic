import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.infrastructure.database.session import get_db
from app.models.sales_history import SalesHistory
from app.models.user import User
from app.schemas.business_data import SalesHistoryResponse, SalesQuery
from app.services.sales_service import get_sale, list_sales

router = APIRouter(prefix="/sales", tags=["sales"])


def validate_sort(value: str) -> str:
    allowed = {"sale_date", "created_at", "quantity", "unit_price"}
    if value not in allowed:
        raise HTTPException(
            status_code=422, detail=f"sort must be one of: {', '.join(sorted(allowed))}"
        )
    return value


@router.get("", response_model=list[SalesHistoryResponse])
def sales(
    query: SalesQuery = Depends(),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[SalesHistory]:
    if query.sale_date_from and query.sale_date_to and query.sale_date_from > query.sale_date_to:
        raise HTTPException(status_code=422, detail="sale_date_from must not be after sale_date_to")
    return list_sales(
        db,
        user.organization_id,
        query.offset,
        query.limit,
        query.product_code,
        query.warehouse_code,
        query.sale_date_from,
        query.sale_date_to,
        validate_sort(query.sort),
        query.order == "desc",
    )


@router.get("/{sale_id}", response_model=SalesHistoryResponse)
def sale(
    sale_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SalesHistory:
    item = get_sale(db, user.organization_id, sale_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sale not found")
    return item
