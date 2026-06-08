from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.shipment_coa import ShipmentCoaOut, ShipmentCoaUpdateRequest
from app.schemas.shipment import (
    ShipmentConfirmRequest,
    ShipmentConfirmResult,
    ShipmentLineListOut,
)
from app.services.shipment_coa_service import get_or_create_shipment_coa, update_shipment_coa as update_shipment_coa_service
from app.services.shipment_confirm_service import confirm_shipment_lines
from app.services.shipment_list_query import list_shipments_for_grid


router = APIRouter(prefix="/shipments", tags=["Shipments"])


@router.get("", response_model=ShipmentLineListOut)
def list_shipments(
    status: str = Query("WAITING"),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    q: Optional[str] = Query(None),
    shipped_from: Optional[date] = Query(None),
    shipped_to: Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    normalized_status = status.strip().upper()

    if normalized_status not in {"WAITING", "DONE", "CANCELED"}:
        raise HTTPException(status_code=422, detail="status must be WAITING, DONE, or CANCELED")

    items, total = list_shipments_for_grid(
        db,
        status=normalized_status,
        page=page,
        size=size,
        q=q,
        shipped_from=shipped_from,
        shipped_to=shipped_to,
    )

    return ShipmentLineListOut(
        items=items,
        total=total,
        page=page,
        size=size,
    )


@router.post("/confirm", response_model=ShipmentConfirmResult)
def confirm_shipments(
    payload: ShipmentConfirmRequest,
    db: Session = Depends(get_db),
):
    return confirm_shipment_lines(db, payload.shipment_line_ids)


@router.get("/{order_line_id}/coa", response_model=ShipmentCoaOut)
def get_shipment_coa(
    order_line_id: int,
    db: Session = Depends(get_db),
):
    return get_or_create_shipment_coa(db, order_line_id)


@router.patch("/{order_line_id}/coa", response_model=ShipmentCoaOut)
def update_shipment_coa(
    order_line_id: int,
    payload: ShipmentCoaUpdateRequest,
    db: Session = Depends(get_db),
):
    return update_shipment_coa_service(db, order_line_id, payload)
