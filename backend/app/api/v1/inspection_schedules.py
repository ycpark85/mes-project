# app/api/v1/inspection_schedules.py
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.inspection_schedule import InspectionSchedule
from app.models.lot import Lot
from app.models.order_line import OrderLine
from app.models.partner import Partner
from app.models.product import Product
from app.models.lot_step import LotStep
from app.schemas.inspection_schedule import (
    InspectionScheduleCreate,
    InspectionScheduleListItemOut,
    InspectionScheduleOut,
    InspectionScheduleReorderIn,
    InspectionScheduleUpdate,
)
from app.services.ship_qty_policy import calculate_ship_qty



router = APIRouter(prefix="/inspection-schedules", tags=["InspectionSchedule"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@router.post("", response_model=InspectionScheduleOut, status_code=status.HTTP_201_CREATED)
def create_inspection_schedule(payload: InspectionScheduleCreate, db: Session = Depends(get_db)):
    # 1) LOT 존재 검증
    lot = db.get(Lot, payload.lot_id)
    if not lot:
        raise HTTPException(status_code=404, detail="Lot not found")

    # 2) 해당 일자의 day_seq = MAX + 1 (CANCELED 제외)
    max_seq = db.execute(
        select(func.coalesce(func.max(InspectionSchedule.day_seq), 0)).where(
            InspectionSchedule.inspection_date == payload.inspection_date,
            InspectionSchedule.status != "CANCELED",
        )
    ).scalar_one()
    next_seq = int(max_seq) + 1

    # 3) 생성 (status 기본 WAITING)
    obj = InspectionSchedule(
        lot_id=payload.lot_id,
        inspection_date=payload.inspection_date,
        status="WAITING",
        day_seq=next_seq,
        memo=payload.memo,
    )

    try:
        db.add(obj)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Inspection schedule already exists for this lot and date",
        )

    db.refresh(obj)
    return obj


@router.patch("/{inspection_schedule_id}", response_model=InspectionScheduleOut)
def update_inspection_schedule(
    inspection_schedule_id: int,
    payload: InspectionScheduleUpdate,
    db: Session = Depends(get_db),
):
    obj = db.get(InspectionSchedule, inspection_schedule_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Inspection schedule not found")

    # 상태 검증: 검수 시작 전까지만 변경 가능
    if obj.status not in ("WAITING", "RECEIVED"):
        raise HTTPException(
            status_code=409,
            detail="Schedule can be updated only in WAITING/RECEIVED status",
        )

    if payload.memo is not None:
        obj.memo = payload.memo

    def resequence_by_date(target_date: date):
        rows = db.execute(
            select(InspectionSchedule)
            .where(
                InspectionSchedule.inspection_date == target_date,
                InspectionSchedule.status.in_(("WAITING", "RECEIVED")),
            )
            .order_by(
                InspectionSchedule.day_seq.asc(),
                InspectionSchedule.inspection_schedule_id.asc(),
            )
        ).scalars().all()

        for idx, row in enumerate(rows, start=1):
            row.day_seq = idx

    if payload.inspection_date is not None and payload.inspection_date != obj.inspection_date:
        today_kst = datetime.now(ZoneInfo("Asia/Seoul")).date()
        if payload.inspection_date < today_kst:
            raise HTTPException(
                status_code=409,
                detail="Inspection schedule date cannot be changed to a past date",
            )

        old_date = obj.inspection_date

        # 새 날짜 기준 임시로 뒤에 붙임
        max_seq = db.execute(
            select(func.coalesce(func.max(InspectionSchedule.day_seq), 0)).where(
                InspectionSchedule.inspection_date == payload.inspection_date,
                InspectionSchedule.status != "CANCELED",
            )
        ).scalar_one()

        obj.inspection_date = payload.inspection_date
        obj.day_seq = int(max_seq) + 1

        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=409, detail="Duplicate (lot_id, inspection_date) is not allowed")

        # 이동 후 old/new 날짜 각각 재정렬
        resequence_by_date(old_date)
        resequence_by_date(payload.inspection_date)

        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=409, detail="Failed to resequence inspection schedules")

        db.refresh(obj)
        return obj

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Duplicate (lot_id, inspection_date) is not allowed")

    db.refresh(obj)
    return obj


@router.post("/{inspection_schedule_id}/receive", response_model=InspectionScheduleOut)
def receive_inspection_schedule(
    inspection_schedule_id: int,
    db: Session = Depends(get_db),
):
    obj = db.get(InspectionSchedule, inspection_schedule_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Inspection schedule not found")

    if obj.status != "WAITING":
        raise HTTPException(status_code=409, detail="Only WAITING schedule can be received")
    
     # ✅ 외주공정 완료 게이트
    remaining = db.execute(
        select(func.count())
        .select_from(LotStep)
        .where(
            LotStep.lot_id == obj.lot_id,
            LotStep.process_type == "OUTSOURCE",
            LotStep.status.notin_(("DONE", "CANCELED")),
        )
    ).scalar_one()

    if int(remaining) > 0:
        raise HTTPException(status_code=409, detail="OUTSOURCE steps must be DONE before receiving")


    obj.status = "RECEIVED"
    obj.received_at = _utcnow()  # ✅ SSOT 반영

    db.commit()
    db.refresh(obj)
    return obj


@router.post("/{inspection_schedule_id}/start", response_model=InspectionScheduleOut)
def start_inspection_schedule(
    inspection_schedule_id: int,
    db: Session = Depends(get_db),
):
    obj = db.get(InspectionSchedule, inspection_schedule_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Inspection schedule not found")

    if obj.status != "RECEIVED":
        raise HTTPException(status_code=409, detail="Only RECEIVED schedule can be started")
    
    # ✅ 오늘 날짜(Asia/Seoul)만 시작 가능
    today_kst = datetime.now(ZoneInfo("Asia/Seoul")).date()
    if obj.inspection_date != today_kst:
        raise HTTPException(status_code=409, detail="Inspection can be started only for today's schedule")

    obj.status = "IN_PROGRESS"
    obj.started_at = _utcnow()

    db.commit()
    db.refresh(obj)
    return obj


@router.post("/{inspection_schedule_id}/cancel", response_model=InspectionScheduleOut)
def cancel_inspection_schedule(
    inspection_schedule_id: int,
    db: Session = Depends(get_db),
):
    obj = db.get(InspectionSchedule, inspection_schedule_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Inspection schedule not found")

    if obj.status not in ("WAITING", "RECEIVED"):
        raise HTTPException(status_code=409, detail="Only WAITING/RECEIVED schedule can be canceled")

    obj.status = "CANCELED"

    db.commit()
    db.refresh(obj)
    return obj


@router.put("/reorder", response_model=list[InspectionScheduleOut])
def reorder_inspection_schedules(
    payload: InspectionScheduleReorderIn,
    db: Session = Depends(get_db),
):
    if len(payload.ordered_ids) != len(set(payload.ordered_ids)):
        raise HTTPException(status_code=409, detail="Duplicated ids in ordered_ids")

    rows = db.execute(
        select(InspectionSchedule)
        .where(
            InspectionSchedule.inspection_date == payload.inspection_date,
            InspectionSchedule.status.in_(("WAITING", "RECEIVED")),
        )
        .with_for_update()
    ).scalars().all()

    if not rows:
        raise HTTPException(status_code=404, detail="No reorder targets for this date")

    target_ids = {r.inspection_schedule_id for r in rows}
    req_ids = payload.ordered_ids

    if set(req_ids) != target_ids:
        raise HTTPException(
            status_code=409,
            detail="ordered_ids must match ALL schedules of that date (WAITING/RECEIVED)",
        )

    try:
        max_seq = db.execute(
            select(func.coalesce(func.max(InspectionSchedule.day_seq), 0)).where(
                InspectionSchedule.inspection_date == payload.inspection_date
            )
        ).scalar_one()

        temp_base = int(max_seq) + 10000

        for idx, sid in enumerate(req_ids, start=1):
            db.execute(
                update(InspectionSchedule)
                .where(InspectionSchedule.inspection_schedule_id == sid)
                .values(day_seq=temp_base + idx)
            )

        for idx, sid in enumerate(req_ids, start=1):
            db.execute(
                update(InspectionSchedule)
                .where(InspectionSchedule.inspection_schedule_id == sid)
                .values(day_seq=idx)
            )

        db.commit()

        out_rows = db.execute(
            select(InspectionSchedule).where(InspectionSchedule.inspection_schedule_id.in_(req_ids))
        ).scalars().all()
        out_map = {r.inspection_schedule_id: r for r in out_rows}
        return [out_map[sid] for sid in req_ids]

    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Reorder failed due to constraint violation")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"Reorder failed: {type(e).__name__}")


@router.get("", response_model=list[InspectionScheduleListItemOut])
def list_inspection_schedules(
    inspection_date_from: Optional[date] = None,
    inspection_date_to: Optional[date] = None,
    status: Optional[str] = None,
    partner_q: Optional[str] = None,
    product_q: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    q = (
        select(
            InspectionSchedule.inspection_schedule_id,
            InspectionSchedule.lot_id,
            Lot.lot_no,
            InspectionSchedule.inspection_date,
            InspectionSchedule.status,
            InspectionSchedule.day_seq,
            Lot.due_date,
            Partner.name.label("partner_name"),
            Product.product_code,
            Product.product_name,
            Lot.lot_qty,
            OrderLine.order_qty,
            InspectionSchedule.memo,
        )
        .select_from(InspectionSchedule)
        .join(Lot, Lot.lot_id == InspectionSchedule.lot_id)
        .join(OrderLine, OrderLine.order_line_id == Lot.order_line_id)
        .join(Partner, Partner.partner_id == OrderLine.partner_id)
        .join(Product, Product.product_id == OrderLine.product_id)
    )

    if inspection_date_from is not None:
        q = q.where(InspectionSchedule.inspection_date >= inspection_date_from)
    if inspection_date_to is not None:
        q = q.where(InspectionSchedule.inspection_date <= inspection_date_to)
    if status is not None:
        q = q.where(InspectionSchedule.status == status)

    if partner_q:
        q = q.where(Partner.name.ilike(f"%{partner_q}%"))

    if product_q:
        q = q.where(
            (Product.product_name.ilike(f"%{product_q}%"))
            | (Product.product_code.ilike(f"%{product_q}%"))
        )

    q = (
        q.order_by(
            InspectionSchedule.inspection_date.asc(),
            InspectionSchedule.day_seq.asc().nulls_last(),
            InspectionSchedule.inspection_schedule_id.asc(),
        )
        .limit(limit)
        .offset(offset)
    )

    rows = db.execute(q).mappings().all()

    items = []
    for row in rows:
        row_dict = dict(row)
        row_dict["ship_qty"] = calculate_ship_qty(
            row_dict["partner_name"],
            row_dict["order_qty"],
        )
        items.append(row_dict)

    return items


@router.get("/{inspection_schedule_id}", response_model=InspectionScheduleOut)
def get_inspection_schedule(
    inspection_schedule_id: int,
    db: Session = Depends(get_db),
):
    obj = db.get(InspectionSchedule, inspection_schedule_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Inspection schedule not found")
    return obj