from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.crud.order_line import order_line_crud
from app.models.order_line import OrderLine
from app.models.partner import Partner
from app.models.product_inventory_movement import ProductInventoryMovement
from app.schemas.order_line import OrderLineShortCloseRequest, OrderLineStatus
from app.services.ship_qty_policy import calculate_ship_qty


def get_remaining_ship_qty(db: Session, order_line: OrderLine) -> int:
    partner = db.get(Partner, order_line.partner_id)
    partner_name = partner.name if partner else ""

    ship_target_qty = int(calculate_ship_qty(partner_name, int(order_line.order_qty or 0)) or 0)
    already_shipped_qty = int(
        db.execute(
            select(func.coalesce(func.sum(-ProductInventoryMovement.qty), 0)).where(
                ProductInventoryMovement.order_line_id == order_line.order_line_id,
                ProductInventoryMovement.movement_type == "SHIP_OUT",
            )
        ).scalar_one()
        or 0
    )

    return max(ship_target_qty - already_shipped_qty, 0)


def short_close_order_line_status(
    db: Session,
    order_line_id: int,
    payload: OrderLineShortCloseRequest,
) -> OrderLine:
    order_line = order_line_crud.get(db, order_line_id)
    if not order_line or not order_line.is_active:
        raise HTTPException(status_code=404, detail="OrderLine not found")

    if order_line.status != OrderLineStatus.CLOSED.value:
        raise HTTPException(status_code=409, detail="부족종료는 CLOSED 상태 수주에서만 가능합니다.")

    remaining_ship_qty = get_remaining_ship_qty(db, order_line)
    if remaining_ship_qty <= 0:
        raise HTTPException(status_code=409, detail="부족수량이 없어 부족종료 대상이 아닙니다.")

    memo_suffix = f"[SHORT_CLOSE] remaining_ship_qty={remaining_ship_qty}"
    if payload.memo and payload.memo.strip():
        memo_suffix = f"{memo_suffix} / {payload.memo.strip()}"

    if order_line.memo and order_line.memo.strip():
        order_line.memo = f"{order_line.memo}\n{memo_suffix}"
    else:
        order_line.memo = memo_suffix

    order_line.status = OrderLineStatus.DONE.value

    db.flush()
    return order_line
