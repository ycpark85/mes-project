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
from app.services.ship_qty_policy import calculate_ship_qty


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)





def upsert_inspection_result(
    db: Session,
    inspection_schedule_id: int,
    *,
    good_qty: int,
    defect_ship_qty: int,
    defect_qty: int,
    is_partial: bool,
    next_inspection_date: Optional[date],
    partial_reason: Optional[str],
    defects: Sequence[DefectLineIn],
    actor: str,
) -> tuple[InspectionResult, str, Optional[int]]:
    """
    - schedule.status == IN_PROGRESS 에서만 허용
    - inspected_qty = good_qty + defect_ship_qty + defect_qty (서버 계산)
    - defects/attachments: MVP 안전형(전체 삭제 후 재삽입)
    - 불량내역은 유형/메모/첨부 기록용으로만 사용
    - is_partial=true: schedule=PARTIAL_DONE + next schedule 자동 생성(RECEIVED)
    - is_partial=false: schedule=DONE + lot DONE 전이(활성 schedule 없음)
    """

    # 1) schedule row lock
    sch = db.execute(
        select(InspectionSchedule)
        .where(InspectionSchedule.inspection_schedule_id == inspection_schedule_id)
        .with_for_update()
    ).scalar_one_or_none()

    if not sch:
        raise HTTPException(status_code=404, detail="inspection_schedule not found")

    # 2) 상태 검증
    if sch.status != "IN_PROGRESS":
        raise HTTPException(status_code=409, detail="Only IN_PROGRESS schedule can be saved as result")

    # 3) partial 검증
    if is_partial:
        if not next_inspection_date:
            raise HTTPException(status_code=422, detail="next_inspection_date is required when is_partial=true")
    else:
        next_inspection_date = None

    # 4) 수량 계산 (서버 SSOT)
    inspected_qty = good_qty + defect_ship_qty + defect_qty

    # 5) 불량유형 존재/활성 검증
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

    # 6) inspection_result upsert
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
        db.flush()

    # 7) defects/attachments: 전체 삭제 후 재삽입
    _replace_defects_and_attachments(db, inspection_result_id=result.inspection_result_id, defects=defects)

    created_next_id: Optional[int] = None

    # 8) schedule 상태 전이 + 후속 처리
    # 8) schedule 상태 전이 + 후속 처리
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
    if order_line and order_line.status != "CANCELED":
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

def _apply_inventory_for_result(
    db: Session,
    *,
    result: InspectionResult,
    schedule: InspectionSchedule,
) -> None:
    existing = db.execute(
        select(ProductInventoryMovement.inventory_movement_id)
        .where(
            ProductInventoryMovement.source_type == "INSPECTION_RESULT",
            ProductInventoryMovement.source_id == result.inspection_result_id,
        )
        .limit(1)
    ).scalar_one_or_none()

    if existing is not None:
        return

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

    ship_target_qty = calculate_ship_qty(partner_name, int(order_line.order_qty))

    already_shipped_qty = db.execute(
        select(func.coalesce(func.sum(-ProductInventoryMovement.qty), 0))
        .where(
            ProductInventoryMovement.order_line_id == order_line.order_line_id,
            ProductInventoryMovement.movement_type == "SHIP_OUT",
        )
    ).scalar_one()

    remaining_ship_qty = max(ship_target_qty - int(already_shipped_qty or 0), 0)

    sellable_qty = int(result.good_qty or 0) + int(result.defect_ship_qty or 0)

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

    if sellable_qty > 0:
        inventory.current_qty += sellable_qty

        db.add(
            ProductInventoryMovement(
                product_id=lot.product_id,
                movement_type="INSPECTION_IN",
                qty=sellable_qty,
                balance_after=inventory.current_qty,
                source_type="INSPECTION_RESULT",
                source_id=result.inspection_result_id,
                order_line_id=order_line.order_line_id,
                inspection_schedule_id=schedule.inspection_schedule_id,
                inspection_result_id=result.inspection_result_id,
                memo="검수 실적 재고 반영",
            )
        )

    ship_qty = min(int(inventory.current_qty or 0), remaining_ship_qty)

    if ship_qty > 0:
        inventory.current_qty -= ship_qty

        db.add(
            ProductInventoryMovement(
                product_id=lot.product_id,
                movement_type="SHIP_OUT",
                qty=-ship_qty,
                balance_after=inventory.current_qty,
                source_type="INSPECTION_RESULT",
                source_id=result.inspection_result_id,
                order_line_id=order_line.order_line_id,
                inspection_schedule_id=schedule.inspection_schedule_id,
                inspection_result_id=result.inspection_result_id,
                memo=f"검수 실적 출고 반영 / 목표 {ship_target_qty}",
            )
        )

    db.flush()        