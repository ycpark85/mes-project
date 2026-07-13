from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.crud.order_line import order_line_crud
from app.models.order_line import OrderLine
from app.schemas.order_line import OrderLineStatus
from app.schemas.order_line_detail import OrderLineDetailUpdate
from app.services.order_line_update_service import propagate_order_line_due_date
from app.services.production_daily_query import refresh_order_line_snapshot


def update_order_line_detail_fields(
    db: Session,
    order_line_id: int,
    payload: OrderLineDetailUpdate,
) -> OrderLine:
    order_line = order_line_crud.get(db, order_line_id)
    if not order_line or not order_line.is_active:
        raise HTTPException(status_code=404, detail="OrderLine not found")

    if order_line.status in {
        OrderLineStatus.DONE.value,
        OrderLineStatus.CANCELED.value,
    }:
        raise HTTPException(
            status_code=409,
            detail="DONE 또는 CANCELED 상태의 수주는 수정할 수 없습니다.",
        )

    if payload.order_qty <= 0:
        raise HTTPException(status_code=422, detail="order_qty must be greater than 0")

    old_due_date = order_line.due_date

    order_line.due_date = payload.due_date
    order_line.order_qty = payload.order_qty
    order_line.memo = payload.memo
    order_line.updated_at = datetime.now(timezone.utc)

    db.add(order_line)

    if payload.due_date != old_due_date:
        propagate_order_line_due_date(db, order_line_id, payload.due_date)
    else:
        refresh_order_line_snapshot(db, order_line_id)

    db.flush()
    return order_line
