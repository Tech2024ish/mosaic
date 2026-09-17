from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.infrastructure.database.session import get_db
from app.models.user import User
from app.schemas.insights import (
    ComparisonQuery,
    ComparisonResponse,
    InsightsOverviewResponse,
    InsightsQuery,
)
from app.services.insights_service import insights_overview, period_comparison

router = APIRouter(prefix="/insights", tags=["insights"])


def validate_date_range(date_from: date | None, date_to: date | None) -> None:
    if date_from is not None and date_to is not None and date_from > date_to:
        raise HTTPException(status_code=422, detail="date_from must not be after date_to")


@router.get("/overview", response_model=InsightsOverviewResponse)
def overview(
    query: InsightsQuery = Depends(),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> InsightsOverviewResponse:
    validate_date_range(query.date_from, query.date_to)
    return insights_overview(
        db,
        user.organization_id,
        query.date_from,
        query.date_to,
        query.product_code,
        query.warehouse_code,
        query.limit,
    )


@router.get("/comparison", response_model=ComparisonResponse)
def comparison(
    query: ComparisonQuery = Depends(),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ComparisonResponse:
    validate_date_range(query.date_from, query.date_to)
    if query.date_from is None or query.date_to is None:
        raise HTTPException(
            status_code=422,
            detail="date_from and date_to are required for period comparison",
        )
    return period_comparison(
        db,
        user.organization_id,
        query.date_from,
        query.date_to,
        query.product_code,
        query.warehouse_code,
    )
