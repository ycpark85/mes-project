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
from app.schemas.inspection_result import DefectLineIn


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


ACTIVE_SCHEDULE_STATUSES = ("WAITING", "RECEIVED", "IN_PROGRESS", "PARTIAL_DONE")


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
    - disposition 합계 검증:
        Σ(SHIP_AS_IS) == defect_ship_qty
        Σ(NOT_SHIPPABLE) == defect_qty
    - is_partial=true:
        schedule=PARTIAL_DONE + next schedule 자동 생성(RECEIVED)
    - is_partial=false:
        schedule=DONE + lot DONE 전이(활성 schedule 없음)
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

    # 5) disposition 합계 검증
    ship_sum = sum(d.defect_qty for d in defects if d.disposition == "SHIP_AS_IS")
    not_ship_sum = sum(d.defect_qty for d in defects if d.disposition == "NOT_SHIPPABLE")

    if ship_sum != defect_ship_qty:
        raise HTTPException(
            status_code=422,
            detail=f"Σ(SHIP_AS_IS)={ship_sum} must equal defect_ship_qty={defect_ship_qty}",
        )
    if not_ship_sum != defect_qty:
        raise HTTPException(
            status_code=422,
            detail=f"Σ(NOT_SHIPPABLE)={not_ship_sum} must equal defect_qty={defect_qty}",
        )

    # 6) defect_type 존재/활성 검증
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

    # 7) inspection_result upsert
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

    # 8) defects/attachments: 전체 삭제 후 재삽입
    _replace_defects_and_attachments(db, inspection_result_id=result.inspection_result_id, defects=defects)

    created_next_id: Optional[int] = None

    # 9) schedule 상태 전이 + 후속 처리
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
    else:
        sch.status = "DONE"
        sch.finished_at = now

        _maybe_close_lot(db, lot_id=sch.lot_id)

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
            delete(InspectionDefect).where(InspectionDefect.inspection_defect_id.in_(defect_ids))
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


def _maybe_close_lot(db: Session, *, lot_id: int) -> None:
    exists_active = db.execute(
        select(InspectionSchedule.inspection_schedule_id)
        .where(
            InspectionSchedule.lot_id == lot_id,
            InspectionSchedule.status.in_(ACTIVE_SCHEDULE_STATUSES),
        )
        .limit(1)
    ).scalar_one_or_none()

    if exists_active is None:
        lot = db.get(Lot, lot_id)
        if lot:
            lot.status = "DONE"
            db.flush()