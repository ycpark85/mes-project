from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional, Sequence

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.defect_type import DefectType
from app.models.inspection_defect import InspectionDefect
from app.models.inspection_defect_attachment import InspectionDefectAttachment
from app.models.inspection_result import InspectionResult
from app.models.inspection_schedule import InspectionSchedule
from app.models.lot import Lot
from app.models.order_line import OrderLine
from app.schemas.inspection_result import DefectLineIn
from sqlalchemy import func
from app.models.partner import Partner
from app.models.product_inventory import ProductInventory
from app.models.product_inventory_movement import ProductInventoryMovement
from app.models.shipment_line import ShipmentLine
from app.services.ship_qty_policy import calculate_ship_qty, is_stock_replenishment_partner


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)





def upsert_inspection_result(
    db: Session,
    inspection_schedule_id: int,
    *,
    good_qty: int,
    defect_ship_qty: int,
    defect_qty: int,
    stock_ship_qty: int,
    result_ship_qty: int,
    stock_in_qty: int,
    is_partial: bool,
    next_inspection_date: Optional[date],
    partial_reason: Optional[str],
    memo: Optional[str],
    defects: Sequence[DefectLineIn],
    actor: str,
) -> tuple[InspectionResult, str, Optional[int]]:
    """
    - schedule.status == IN_PROGRESS 에서만 허용
    - inspected_qty = good_qty + defect_ship_qty + defect_qty (서버 계산)
    - sellable_qty = good_qty + defect_ship_qty
    - result_ship_qty + stock_in_qty == sellable_qty
    - defects/attachments: 전체 삭제 후 재삽입
    - is_partial=true: schedule=PARTIAL_DONE + next schedule 자동 생성(RECEIVED)
    - is_partial=false: schedule=DONE + 재고/출하 반영
    """
    sch = db.execute(
        select(InspectionSchedule)
        .where(InspectionSchedule.inspection_schedule_id == inspection_schedule_id)
        .with_for_update()
    ).scalar_one_or_none()
    if not sch:
        raise HTTPException(status_code=404, detail="inspection_schedule not found")

    if sch.status != "IN_PROGRESS":
        raise HTTPException(status_code=409, detail="Only IN_PROGRESS schedule can be saved as result")

    if is_partial:
        if not next_inspection_date:
            raise HTTPException(status_code=422, detail="next_inspection_date is required when is_partial=true")
    else:
        next_inspection_date = None

    inspected_qty = good_qty + defect_ship_qty + defect_qty
    sellable_qty = good_qty + defect_ship_qty

    if result_ship_qty + stock_in_qty != sellable_qty:
        raise HTTPException(
            status_code=422,
            detail="result_ship_qty + stock_in_qty must equal good_qty + defect_ship_qty",
        )

    if defects:
        defect_type_ids = sorted({d.defect_type_id for d in defects})
        rows = db.execute(
            select(DefectType.defect_type_id).where(
                DefectType.defect_type_id.in_(defect_type_ids),
                DefectType.is_active.is_(True),
            )
        ).scalars().all()

        if set(rows) != set(defect_type_ids):
            raise HTTPException(status_code=422, detail="Invalid or inactive defect_type_id exists")

    now = _utcnow()

    result = db.execute(
        select(InspectionResult).where(InspectionResult.inspection_schedule_id == inspection_schedule_id)
    ).scalar_one_or_none()

    if result is None:
        result = InspectionResult(
            inspection_schedule_id=inspection_schedule_id,
            good_qty=good_qty,
            defect_ship_qty=defect_ship_qty,
            defect_qty=defect_qty,
            inspected_qty=inspected_qty,
            is_partial=is_partial,
            next_inspection_date=next_inspection_date,
            partial_reason=partial_reason,
            memo=memo,
            created_by=actor,
        )
        db.add(result)
        db.flush()
    else:
        result.good_qty = good_qty
        result.defect_ship_qty = defect_ship_qty
        result.defect_qty = defect_qty
        result.inspected_qty = inspected_qty
        result.is_partial = is_partial
        result.next_inspection_date = next_inspection_date
        result.partial_reason = partial_reason
        result.memo = memo
        db.flush()

    _replace_defects_and_attachments(
        db,
        inspection_result_id=result.inspection_result_id,
        defects=defects,
    )

    created_next_id: Optional[int] = None

    if is_partial:
        sch.status = "PARTIAL_DONE"
        sch.finished_at = now

        base_received_at = sch.received_at or now
        created_next_id = _create_next_schedule(
            db=db,
            lot_id=sch.lot_id,
            inspection_date=next_inspection_date,  # type: ignore[arg-type]
            received_at=base_received_at,
        )
        db.flush()
        _sync_lot_status_from_inspection_schedules(db, lot_id=sch.lot_id)
    else:
        sch.status = "DONE"
        sch.finished_at = now
        db.flush()

        _sync_lot_status_from_inspection_schedules(db, lot_id=sch.lot_id)

        _apply_inventory_for_result(
            db=db,
            result=result,
            schedule=sch,
            stock_ship_qty=stock_ship_qty,
            result_ship_qty=result_ship_qty,
            stock_in_qty=stock_in_qty,
        )
        
        db.flush()
        

    return result, sch.status, created_next_id

   


def _replace_defects_and_attachments(
    db: Session,
    *,
    inspection_result_id: int,
    defects: Sequence[DefectLineIn],
):
    defect_ids = db.execute(
        select(InspectionDefect.inspection_defect_id).where(
            InspectionDefect.inspection_result_id == inspection_result_id
        )
    ).scalars().all()

    if defect_ids:
        db.execute(
            delete(InspectionDefectAttachment).where(
                InspectionDefectAttachment.inspection_defect_id.in_(defect_ids)
            )
        )
        db.execute(
            delete(InspectionDefect).where(
                InspectionDefect.inspection_defect_id.in_(defect_ids)
            )
        )
        db.flush()

    for line in defects:
        defect = InspectionDefect(
            inspection_result_id=inspection_result_id,
            defect_type_id=line.defect_type_id,
            defect_qty=line.defect_qty,
            disposition=line.disposition,
            memo=line.memo,
        )
        db.add(defect)
        db.flush()

        for att in line.attachments:
            db.add(
                InspectionDefectAttachment(
                    inspection_defect_id=defect.inspection_defect_id,
                    file_uri=att.file_uri,
                    file_name=att.file_name,
                    mime_type=att.mime_type,
                    memo=att.memo,
                )
            )

    db.flush()


def _create_next_schedule(
    db: Session,
    *,
    lot_id: int,
    inspection_date: date,
    received_at: datetime,
) -> int:
    """
    - status=RECEIVED
    - day_seq: 동일 날짜(status!=CANCELED) row들을 FOR UPDATE로 잠금 후 파이썬 max+1
    """
    locked_seqs = db.execute(
        select(InspectionSchedule.day_seq)
        .where(
            InspectionSchedule.inspection_date == inspection_date,
            InspectionSchedule.status != "CANCELED",
        )
        .with_for_update()
    ).scalars().all()

    max_seq = 0
    for s in locked_seqs:
        if s is not None and int(s) > max_seq:
            max_seq = int(s)

    next_seq = max_seq + 1

    new_sch = InspectionSchedule(
        lot_id=lot_id,
        inspection_date=inspection_date,
        status="RECEIVED",
        received_at=received_at,
        day_seq=next_seq,
    )
    db.add(new_sch)

    try:
        db.flush()
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Duplicate (lot_id, inspection_date) is not allowed")

    return new_sch.inspection_schedule_id


def _sync_order_line_status_from_lot(db: Session, *, lot: Lot) -> None:
    exists_not_done_lot = db.execute(
        select(Lot.lot_id)
        .where(
            Lot.order_line_id == lot.order_line_id,
            Lot.status != "CANCELED",
            Lot.status != "DONE",
        )
        .limit(1)
    ).scalar_one_or_none()

    if exists_not_done_lot is not None:
        return

    order_line = db.get(OrderLine, lot.order_line_id)

    if not order_line or order_line.status == "CANCELED":
        return

    order_line.status = "DONE"
    db.flush()


def _sync_lot_status_from_inspection_schedules(
    db: Session,
    *,
    lot_id: int,
) -> None:
    lot = db.get(Lot, lot_id)
    if not lot:
        return

    statuses = (
        db.execute(
            select(InspectionSchedule.status)
            .where(
                InspectionSchedule.lot_id == lot_id,
                InspectionSchedule.status != "CANCELED",
            )
        )
        .scalars()
        .all()
    )

    if not statuses:
        return

    next_status: str | None = None

    if "IN_PROGRESS" in statuses:
        next_status = "IN_PROGRESS"
    elif "RECEIVED" in statuses:
        next_status = "RECEIVED"
    elif "PARTIAL_DONE" in statuses:
        next_status = "PARTIAL_DONE"
    elif "WAITING" in statuses:
        next_status = "WAITING"
    elif all(status == "DONE" for status in statuses):
        next_status = "DONE"

    if next_status is None:
        return

    lot.status = next_status
    db.flush()

    if next_status == "DONE":
        _sync_order_line_status_from_lot(db, lot=lot)

def _get_fifo_stock_lot_allocations(
    db: Session,
    *,
    product_id: int,
    current_lot_id: int,
    inspection_result_id: int,
    stock_ship_qty: int,
) -> list[tuple[int, int]]:
    if stock_ship_qty <= 0:
        return []

    stock_in_rows = (
        db.execute(
            select(
                Lot.lot_id,
                Lot.created_date,
                func.coalesce(func.sum(ProductInventoryMovement.qty), 0).label("stock_in_qty"),
            )
            .select_from(ProductInventoryMovement)
            .join(
                InspectionResult,
                InspectionResult.inspection_result_id
                == ProductInventoryMovement.inspection_result_id,
            )
            .join(
                InspectionSchedule,
                InspectionSchedule.inspection_schedule_id
                == InspectionResult.inspection_schedule_id,
            )
            .join(Lot, Lot.lot_id == InspectionSchedule.lot_id)
            .where(
                ProductInventoryMovement.product_id == product_id,
                ProductInventoryMovement.movement_type == "INSPECTION_IN",
                ProductInventoryMovement.qty > 0,
                Lot.lot_id != current_lot_id,
            )
            .group_by(
                Lot.lot_id,
                Lot.created_date,
            )
            .order_by(
                Lot.created_date.asc(),
                Lot.lot_id.asc(),
            )
        )
        .mappings()
        .all()
    )

    allocated_rows = (
        db.execute(
            select(
                ShipmentLine.lot_id,
                func.coalesce(func.sum(ShipmentLine.ship_qty), 0).label("allocated_qty"),
            )
            .where(
                ShipmentLine.product_id == product_id,
                ShipmentLine.status.in_(("WAITING", "DONE")),
                ShipmentLine.lot_id.is_not(None),
                ShipmentLine.lot_id != current_lot_id,
                (ShipmentLine.inspection_result_id.is_(None))
                | (ShipmentLine.inspection_result_id != inspection_result_id),
            )
            .group_by(ShipmentLine.lot_id)
        )
        .mappings()
        .all()
    )

    allocated_map = {
        int(row["lot_id"]): int(row["allocated_qty"] or 0)
        for row in allocated_rows
    }

    remaining_qty = stock_ship_qty
    allocations: list[tuple[int, int]] = []

    for row in stock_in_rows:
        lot_id = int(row["lot_id"])
        stock_in_qty = int(row["stock_in_qty"] or 0)
        allocated_qty = allocated_map.get(lot_id, 0)
        available_qty = max(stock_in_qty - allocated_qty, 0)

        if available_qty <= 0:
            continue

        ship_qty = min(available_qty, remaining_qty)

        if ship_qty > 0:
            allocations.append((lot_id, ship_qty))
            remaining_qty -= ship_qty

        if remaining_qty <= 0:
            break

    if remaining_qty > 0:
        raise HTTPException(
            status_code=422,
            detail="기존재고 출하대기 수량을 FIFO LOT 재고로 배정할 수 없습니다.",
        )

    return allocations


def _create_stock_shipment_lines_by_fifo(
    db: Session,
    *,
    order_line: OrderLine,
    product_id: int,
    current_lot_id: int,
    inspection_result_id: int,
    stock_ship_qty: int,
) -> None:
    allocations = _get_fifo_stock_lot_allocations(
        db,
        product_id=product_id,
        current_lot_id=current_lot_id,
        inspection_result_id=inspection_result_id,
        stock_ship_qty=stock_ship_qty,
    )

    for lot_id, ship_qty in allocations:
        db.add(
            ShipmentLine(
                order_line_id=order_line.order_line_id,
                product_id=product_id,
                lot_id=lot_id,
                inspection_result_id=inspection_result_id,
                source_type="STOCK",
                status="WAITING",
                ship_qty=ship_qty,
                shipped_qty=0,
                memo="검수 실적 저장 시 기존 재고 출하대기 FIFO LOT 생성",
            )
        )

def _apply_inventory_for_result(
    db: Session,
    *,
    result: InspectionResult,
    schedule: InspectionSchedule,
    stock_ship_qty: int,
    result_ship_qty: int,
    stock_in_qty: int,
) -> None:
    lot = db.execute(
        select(Lot)
        .where(Lot.lot_id == schedule.lot_id)
        .with_for_update()
    ).scalar_one_or_none()
    if lot is None:
        raise HTTPException(status_code=404, detail="lot not found")

    order_line = db.execute(
        select(OrderLine)
        .where(OrderLine.order_line_id == lot.order_line_id)
        .with_for_update()
    ).scalar_one_or_none()
    if order_line is None:
        raise HTTPException(status_code=404, detail="order_line not found")

    partner = db.get(Partner, order_line.partner_id)
    partner_name = partner.name if partner else ""
    partner_business_no = partner.business_no if partner else ""

    is_stock_replenishment = is_stock_replenishment_partner(
        partner_name,
        partner_business_no,
    )

    inventory = db.execute(
        select(ProductInventory)
        .where(ProductInventory.product_id == lot.product_id)
        .with_for_update()
    ).scalar_one_or_none()

    if inventory is None:
        inventory = ProductInventory(
            product_id=lot.product_id,
            current_qty=0,
        )
        db.add(inventory)
        db.flush()

    existing_movements = db.execute(
        select(ProductInventoryMovement)
        .where(
            ProductInventoryMovement.inspection_result_id == result.inspection_result_id,
            ProductInventoryMovement.source_type.in_(("INSPECTION_RESULT", "INSPECTION_RESULT_IN")),
        )
        .with_for_update()
    ).scalars().all()

    for mv in existing_movements:
        if mv.movement_type == "INSPECTION_IN":
            inventory.current_qty -= int(mv.qty or 0)
        elif mv.movement_type == "SHIP_OUT":
            inventory.current_qty -= int(mv.qty or 0)

        db.delete(mv)

    existing_shipment_lines = db.execute(
        select(ShipmentLine)
        .where(
            ShipmentLine.inspection_result_id == result.inspection_result_id,
            ShipmentLine.status != "CANCELED",
        )
        .with_for_update()
    ).scalars().all()

    if any(line.status == "DONE" for line in existing_shipment_lines):
        raise HTTPException(
            status_code=409,
            detail="이미 출하 완료된 출하대기 건이 있어 검수실적을 수정할 수 없습니다.",
        )

    for line in existing_shipment_lines:
        db.delete(line)

    db.flush()

    current_stock_qty_before_result_in = int(inventory.current_qty or 0)
    sellable_qty = int(result.good_qty or 0) + int(result.defect_ship_qty or 0)

    if result_ship_qty + stock_in_qty != sellable_qty:
        raise HTTPException(
            status_code=422,
            detail="result_ship_qty + stock_in_qty must equal sellable_qty",
        )

    if stock_ship_qty > current_stock_qty_before_result_in:
        raise HTTPException(
            status_code=422,
            detail=f"stock_ship_qty exceeds current stock. current_stock_qty={current_stock_qty_before_result_in}",
        )

    if is_stock_replenishment:
        ship_target_qty = 0
        remaining_ship_qty = 0
    else:
        ship_target_qty = calculate_ship_qty(
            partner_name,
            int(order_line.order_qty or 0),
        )

        already_shipped_qty = int(
            db.execute(
                select(func.coalesce(func.sum(-ProductInventoryMovement.qty), 0)).where(
                    ProductInventoryMovement.order_line_id == order_line.order_line_id,
                    ProductInventoryMovement.movement_type == "SHIP_OUT",
                )
            ).scalar_one()
            or 0
        )

        remaining_ship_qty = max(ship_target_qty - already_shipped_qty, 0)

    if not is_stock_replenishment:
        requested_ship_waiting_qty = int(stock_ship_qty or 0) + int(result_ship_qty or 0)

        if requested_ship_waiting_qty > remaining_ship_qty:
            raise HTTPException(
                status_code=422,
                detail=f"shipment waiting qty exceeds remaining ship target. remaining_ship_qty={remaining_ship_qty}",
            )

    if sellable_qty > 0:
        inventory.current_qty += sellable_qty
        db.add(
            ProductInventoryMovement(
                product_id=lot.product_id,
                movement_type="INSPECTION_IN",
                qty=sellable_qty,
                balance_after=inventory.current_qty,
                source_type="INSPECTION_RESULT_IN",
                source_id=result.inspection_result_id,
                order_line_id=order_line.order_line_id,
                inspection_schedule_id=schedule.inspection_schedule_id,
                inspection_result_id=result.inspection_result_id,
                memo="검수 실적 재고 입고",
            )
        )

    if stock_ship_qty > 0:
        _create_stock_shipment_lines_by_fifo(
            db,
            order_line=order_line,
            product_id=lot.product_id,
            current_lot_id=lot.lot_id,
            inspection_result_id=result.inspection_result_id,
            stock_ship_qty=stock_ship_qty,
        )

    if result_ship_qty > 0:
        db.add(
            ShipmentLine(
                order_line_id=order_line.order_line_id,
                product_id=lot.product_id,
                lot_id=lot.lot_id,
                inspection_result_id=result.inspection_result_id,
                source_type="INSPECTION_RESULT",
                status="WAITING",
                ship_qty=result_ship_qty,
                shipped_qty=0,
                memo="검수 실적 저장 시 검수분 출하대기 생성",
            )
        )

    order_line.status = "DONE"

    db.flush()   