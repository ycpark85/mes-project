from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.production_daily import ProductionDailyListOut
from app.services.production_daily_query import list_production_daily_rows


router = APIRouter(prefix="/production-daily", tags=["ProductionDaily"])


@router.get("", response_model=ProductionDailyListOut)
def list_production_daily(
    page: int = Query(1, ge=1),
    size: int = Query(200, ge=1, le=500),
    status: str = Query("IN_PROGRESS"),
    partner_q: str | None = Query(None),
    product_q: str | None = Query(None),
    db: Session = Depends(get_db),
):
    items, total = list_production_daily_rows(
        db,
        page=page,
        size=size,
        status=status,
        partner_q=partner_q,
        product_q=product_q,
    )

    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
    }
