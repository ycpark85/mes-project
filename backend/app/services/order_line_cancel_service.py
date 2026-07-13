from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.order_line import order_line_crud
from app.models.lot import Lot
from app.models.order_line import OrderLine
from app.schemas.order_line import OrderLineStatus


def cancel_order_line_status(db: Session, order_line_id: int) -> OrderLine:
    order_line = order_line_crud.get(db, order_line_id)
    if not order_line or not order_line.is_active:
        raise HTTPException(status_code=404, detail="OrderLine not found")

    if order_line.status == OrderLineStatus.DONE.value:
        raise HTTPException(
            status_code=409,
            detail="DONE 상태의 수주는 취소할 수 없습니다.",
        )

    if order_line.status == OrderLineStatus.CANCELED.value:
        raise HTTPException(
            status_code=409,
            detail="이미 취소된 수주입니다.",
        )

    lots = _load_order_line_lots(db, order_line_id)
    if _has_any_non_canceled_lot(lots):
        raise HTTPException(
            status_code=409,
            detail="취소되지 않은 LOT가 존재하여 수주를 취소할 수 없습니다. 먼저 모든 LOT를 취소하세요.",
        )

    order_line.status = OrderLineStatus.CANCELED.value
    order_line.updated_at = datetime.now(timezone.utc)

    db.add(order_line)
    db.flush()
    return order_line


def _load_order_line_lots(db: Session, order_line_id: int) -> list[Lot]:
    return (
        db.execute(
            select(Lot)
            .where(Lot.order_line_id == order_line_id)
            .order_by(Lot.created_date.asc(), Lot.lot_id.asc())
        )
        .scalars()
        .all()
    )


def _has_any_non_canceled_lot(lots: list[Lot]) -> bool:
    return any(l.status != "CANCELED" for l in lots)
