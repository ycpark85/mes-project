from __future__ import annotations

from datetime import date

from fastapi import HTTPException
from sqlalchemy import and_, exists, select, update
from sqlalchemy.orm import Session

from app.crud.order_line import order_line_crud
from app.models.lot import Lot
from app.models.lot_step import LotStep
from app.models.order_line import OrderLine
from app.models.shipment_line import ShipmentLine
from app.schemas.order_line import OrderLineStatus, OrderLineUpdate
from app.services.order_line_creation_service import ensure_partner_active, ensure_product_active
from app.services.production_daily_query import refresh_order_line_snapshot


def ensure_no_waiting_stock_reservation_for_plan_change(
    db: Session,
    order_line_id: int,
) -> None:
    waiting_reservation_exists = db.execute(
        select(ShipmentLine.shipment_line_id)
        .where(
            ShipmentLine.order_line_id == order_line_id,
            ShipmentLine.source_type == "STOCK",
            ShipmentLine.status == "WAITING",
        )
        .limit(1)
    ).scalar_one_or_none()

    if waiting_reservation_exists is not None:
        raise HTTPException(
            status_code=409,
            detail="재고출고 확인대기 중에는 거래처, 품목 또는 수주수량을 변경할 수 없습니다. 처리계획을 먼저 확정하세요.",
        )


def propagate_order_line_due_date(db: Session, order_line_id: int, new_due_date: date) -> None:
    sync_lot_due_date_for_not_started(db, order_line_id, new_due_date)
    refresh_order_line_snapshot(db, order_line_id)


def sync_lot_due_date_for_not_started(db: Session, order_line_id: int, new_due_date: date) -> int:
    """
    OrderLine.due_date 변경 시 아직 시작하지 않은 LOT만 lot.due_date를 동기화한다.
    시작 여부는 WAITING이 아닌 lot_step 존재 여부로 판단한다.
    """
    started_exists = (
        select(LotStep.lot_step_id)
        .where(and_(LotStep.lot_id == Lot.lot_id, LotStep.status != "WAITING"))
        .limit(1)
    )

    stmt = (
        update(Lot)
        .where(Lot.order_line_id == order_line_id)
        .where(~exists(started_exists))
        .values(due_date=new_due_date)
    )

    result = db.execute(stmt)
    return result.rowcount or 0


def update_order_line_fields(db: Session, order_line_id: int, payload: OrderLineUpdate) -> OrderLine:
    obj = order_line_crud.get(db, order_line_id)
    if not obj or not obj.is_active:
        raise HTTPException(status_code=404, detail="OrderLine not found")

    data = payload.model_dump(exclude_unset=True)
    requested_due_date = data.get("due_date")

    if obj.status == OrderLineStatus.OPEN.value:
        pass
    elif obj.status == OrderLineStatus.CLOSED.value:
        allow_keys = {"due_date", "memo", "customer_po"}
        forbidden = set(data.keys()) - allow_keys
        if forbidden:
            raise HTTPException(
                status_code=409,
                detail="CLOSED OrderLine can only modify due_date/memo/customer_po",
            )
        data = {k: v for k, v in data.items() if k in allow_keys}
    else:
        forbidden_keys = {
            "order_no",
            "line_no",
            "partner_id",
            "product_id",
            "order_date",
            "due_date",
            "order_qty",
            "uom",
            "priority",
        }
        if any(k in data for k in forbidden_keys):
            raise HTTPException(status_code=409, detail="Only OPEN OrderLine can be modified (except memo/customer_po)")

        allow_keys = {"memo", "customer_po"}
        data = {k: v for k, v in data.items() if k in allow_keys}

    old_due_date = obj.due_date

    if "partner_id" in data:
        ensure_partner_active(db, data["partner_id"])
    if "product_id" in data:
        product = ensure_product_active(db, data["product_id"])
        data["uom"] = product.uom

    plan_affecting_fields = {"partner_id", "product_id", "order_qty"}
    if any(
        key in data and data[key] != getattr(obj, key)
        for key in plan_affecting_fields
    ):
        ensure_no_waiting_stock_reservation_for_plan_change(db, order_line_id)

    order_line_crud.update(db, obj, data)

    if requested_due_date is not None and requested_due_date != old_due_date:
        propagate_order_line_due_date(db, order_line_id, requested_due_date)
    else:
        refresh_order_line_snapshot(db, order_line_id)

    return obj
