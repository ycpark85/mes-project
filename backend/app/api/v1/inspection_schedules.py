# app/api/v1/inspection_schedules.py
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select, update,exists
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.inspection_schedule import InspectionSchedule
from app.models.lot import Lot
from app.models.order_line import OrderLine
from app.models.partner import Partner
from app.models.product import Product
from app.models.lot_step import LotStep
from app.models.outsource_work_group import OutsourceWorkGroup
from app.models.outsource_work_group_item import OutsourceWorkGroupItem
from app.models.outsource_work_instruction import OutsourceWorkInstruction
from app.models.outsource_purchase_order_item import OutsourcePurchaseOrderItem
from app.schemas.inspection_schedule import (
    InspectionScheduleCreate,
    InspectionScheduleListItemOut,
    InspectionScheduleOut,
    InspectionScheduleReorderIn,
    InspectionScheduleUpdate,
    InspectionWorkInstructionTargetListOut,
    InspectionWorkInstructionTargetOut,
)
from app.services.ship_qty_policy import calculate_ship_qty



router = APIRouter(prefix="/inspection-schedules", tags=["InspectionSchedule"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)

def _get_outsource_work_group_items(
    db: Session,
    outsource_work_group_id: int,
) -> list[OutsourceWorkGroupItem]:
    return (
        db.execute(
            select(OutsourceWorkGroupItem)
            .where(
                OutsourceWorkGroupItem.outsource_work_group_id
                == outsource_work_group_id
            )
            .order_by(
                OutsourceWorkGroupItem.outsource_work_group_item_id.asc()
            )
        )
        .scalars()
        .all()
    )


def _create_single_inspection_schedule(
    db: Session,
    lot_id: int,
    inspection_date: date,
    memo: str | None,
    day_seq: int,
    outsource_work_group_id: int | None = None,
    outsource_work_group_item_id: int | None = None,
) -> InspectionSchedule:
    obj = InspectionSchedule(
        lot_id=lot_id,
        inspection_date=inspection_date,
        status="WAITING",
        day_seq=day_seq,
        memo=memo,
        outsource_work_group_id=outsource_work_group_id,
        outsource_work_group_item_id=outsource_work_group_item_id,
    )

    db.add(obj)
    return obj

def _build_inspection_bundle_no_from_values(
    instruction_no: str | None,
    outsource_work_group_id: int | None,
    group_seq: int | None,
    is_bundle: bool | None,
) -> str | None:
    if not is_bundle:
        return None

    if group_seq is not None:
        return f"G{group_seq}"

    if instruction_no and "-" in instruction_no:
        return instruction_no.split("-")[-1]

    if outsource_work_group_id:
        return f"G{outsource_work_group_id}"

    return None

def _to_diecut_status_label(status: str | None) -> str | None:
    if status is None:
        return "도무송 입고대기"

    if status == "VENDOR_RECEIVED":
        return "도무송 입고완료"

    if status == "WORK_DONE":
        return "도무송 완료"

    if status == "SHIPPED":
        return "도무송 출고완료"

    return status

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

    if next_status == "DONE":
        _sync_order_line_status_from_lot(db, lot=lot)



@router.post("", response_model=InspectionScheduleOut, status_code=status.HTTP_201_CREATED)
def create_inspection_schedule(
    payload: InspectionScheduleCreate,
    db: Session = Depends(get_db),
):
    lot = db.get(Lot, payload.lot_id)

    if not lot:
        raise HTTPException(status_code=404, detail="Lot not found")

    max_seq = db.execute(
        select(func.coalesce(func.max(InspectionSchedule.day_seq), 0)).where(
            InspectionSchedule.inspection_date == payload.inspection_date,
            InspectionSchedule.status != "CANCELED",
        )
    ).scalar_one()

    next_seq = int(max_seq) + 1

    selected_schedule: InspectionSchedule | None = None
    created_schedules: list[InspectionSchedule] = []

    if payload.outsource_work_group_id:
        work_group = db.get(
            OutsourceWorkGroup,
            payload.outsource_work_group_id,
        )

        if not work_group:
            raise HTTPException(
                status_code=404,
                detail="Outsource work group not found",
            )

        group_items = _get_outsource_work_group_items(
            db=db,
            outsource_work_group_id=payload.outsource_work_group_id,
        )

        if not group_items:
            raise HTTPException(
                status_code=409,
                detail="Outsource work group has no items",
            )

        selected_group_item = next(
            (
                group_item
                for group_item in group_items
                if group_item.lot_id == payload.lot_id
            ),
            None,
        )

        if selected_group_item is None:
            raise HTTPException(
                status_code=409,
                detail="Selected lot is not included in outsource work group",
            )

        for group_item in group_items:
            existing_schedule = (
                db.execute(
                    select(InspectionSchedule)
                    .where(
                        InspectionSchedule.lot_id == group_item.lot_id,
                        InspectionSchedule.inspection_date == payload.inspection_date,
                        InspectionSchedule.status != "CANCELED",
                    )
                    .limit(1)
                )
                .scalar_one_or_none()
            )

            if existing_schedule:
                if group_item.lot_id == payload.lot_id:
                    selected_schedule = existing_schedule

                continue

            schedule = _create_single_inspection_schedule(
                db=db,
                lot_id=group_item.lot_id,
                inspection_date=payload.inspection_date,
                memo=payload.memo,
                day_seq=next_seq,
                outsource_work_group_id=work_group.outsource_work_group_id,
                outsource_work_group_item_id=group_item.outsource_work_group_item_id,
            )

            if group_item.lot_id == payload.lot_id:
                selected_schedule = schedule

            created_schedules.append(schedule)
            next_seq += 1

        if selected_schedule is None and created_schedules:
            selected_schedule = created_schedules[0]

        if selected_schedule is None:
            raise HTTPException(
                status_code=409,
                detail="Inspection schedule already exists for this outsource work group",
            )

    else:
        existing_schedule = (
            db.execute(
                select(InspectionSchedule)
                .where(
                    InspectionSchedule.lot_id == payload.lot_id,
                    InspectionSchedule.inspection_date == payload.inspection_date,
                    InspectionSchedule.status != "CANCELED",
                )
                .limit(1)
            )
            .scalar_one_or_none()
        )

        if existing_schedule:
            raise HTTPException(
                status_code=409,
                detail="Inspection schedule already exists for this lot and date",
            )

        selected_schedule = _create_single_inspection_schedule(
            db=db,
            lot_id=payload.lot_id,
            inspection_date=payload.inspection_date,
            memo=payload.memo,
            day_seq=next_seq,
            outsource_work_group_id=payload.outsource_work_group_id,
            outsource_work_group_item_id=payload.outsource_work_group_item_id,
        )

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Inspection schedule already exists for this lot and date",
        )

    db.refresh(selected_schedule)

    return selected_schedule


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

    if obj.outsource_work_group_id:
        work_group = db.get(
            OutsourceWorkGroup,
            obj.outsource_work_group_id,
        )

        if not work_group:
            raise HTTPException(
                status_code=404,
                detail="Outsource work group not found",
            )

        if work_group.status != "SHIPPED":
            raise HTTPException(
                status_code=409,
                detail="Only SHIPPED outsource work group can be received",
            )

        group_schedules = (
            db.execute(
                select(InspectionSchedule)
                .where(
                    InspectionSchedule.outsource_work_group_id
                    == obj.outsource_work_group_id,
                    InspectionSchedule.inspection_date == obj.inspection_date,
                    InspectionSchedule.status == "WAITING",
                )
                .order_by(
                    InspectionSchedule.day_seq.asc(),
                    InspectionSchedule.inspection_schedule_id.asc(),
                )
            )
            .scalars()
            .all()
        )

        if not group_schedules:
            raise HTTPException(
                status_code=409,
                detail="No WAITING inspection schedules for outsource work group",
            )

        now = _utcnow()

        for schedule in group_schedules:
            schedule.status = "RECEIVED"
            schedule.received_at = now

        db.flush()

        for lot_id in {schedule.lot_id for schedule in group_schedules}:
            _sync_lot_status_from_inspection_schedules(db, lot_id=lot_id)

        db.commit()
        db.refresh(obj)
        return obj

    shipped_count = db.execute(
        select(func.count())
        .select_from(OutsourcePurchaseOrderItem)
        .where(
            OutsourcePurchaseOrderItem.lot_id == obj.lot_id,
            OutsourcePurchaseOrderItem.status == "SHIPPED",
        )
    ).scalar_one()

    if int(shipped_count) == 0:
        raise HTTPException(
            status_code=409,
            detail="Only SHIPPED outsource purchase order item can be received",
        )

    obj.status = "RECEIVED"
    obj.received_at = _utcnow()

    db.flush()
    _sync_lot_status_from_inspection_schedules(db, lot_id=obj.lot_id)

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

    db.flush()
    _sync_lot_status_from_inspection_schedules(db, lot_id=obj.lot_id)

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

    lot_id = obj.lot_id

    obj.status = "CANCELED"

    db.flush()
    _sync_lot_status_from_inspection_schedules(db, lot_id=lot_id)

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

@router.get(
    "/work-instruction-targets",
    response_model=InspectionWorkInstructionTargetListOut,
)
def get_inspection_work_instruction_targets(
    partner_q: Optional[str] = None,
    product_q: Optional[str] = None,
    limit: int = 200,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    stmt = (
        select(
            Lot.lot_id,
            Lot.lot_no,
            OutsourceWorkGroup.outsource_work_group_id,
            OutsourceWorkGroupItem.outsource_work_group_item_id,
            OutsourceWorkGroup.group_seq,
            OutsourceWorkGroup.is_bundle,
            OutsourceWorkInstruction.instruction_no,
            Product.product_code,
            Product.product_name,
            Partner.name.label("partner_name"),
            Lot.lot_qty,
            Lot.due_date,
            OutsourceWorkGroup.remark.label("memo"),
        )
        .select_from(OutsourceWorkGroupItem)
        .join(
            OutsourceWorkGroup,
            OutsourceWorkGroup.outsource_work_group_id
            == OutsourceWorkGroupItem.outsource_work_group_id,
        )
        .join(
            OutsourceWorkInstruction,
            OutsourceWorkInstruction.outsource_work_instruction_id
            == OutsourceWorkGroup.outsource_work_instruction_id,
        )
        .join(Lot, Lot.lot_id == OutsourceWorkGroupItem.lot_id)
        .join(OrderLine, OrderLine.order_line_id == Lot.order_line_id)
        .join(Partner, Partner.partner_id == OrderLine.partner_id)
        .join(Product, Product.product_id == Lot.product_id)
        .where(
            ~exists(
                select(1)
                .select_from(InspectionSchedule)
                .where(
                    InspectionSchedule.lot_id == Lot.lot_id,
                    InspectionSchedule.status != "CANCELED",
                )
            )
        )
    )

    if partner_q:
        stmt = stmt.where(Partner.name.ilike(f"%{partner_q.strip()}%"))

    if product_q:
        like = f"%{product_q.strip()}%"
        stmt = stmt.where(
            (Product.product_code.ilike(like))
            | (Product.product_name.ilike(like))
            | (Lot.lot_no.ilike(like))
        )

    stmt = (
        stmt.order_by(
            OutsourceWorkInstruction.instruction_date.desc(),
            OutsourceWorkInstruction.instruction_no.desc(),
            OutsourceWorkGroup.group_seq.asc(),
            Lot.lot_no.asc(),
        )
        .limit(limit)
        .offset(offset)
    )

    rows = db.execute(stmt).mappings().all()

    items: list[InspectionWorkInstructionTargetOut] = []

    for row in rows:
        row_dict = dict(row)

        bundle_no = _build_inspection_bundle_no_from_values(
            instruction_no=row_dict.get("instruction_no"),
            outsource_work_group_id=row_dict.get("outsource_work_group_id"),
            group_seq=row_dict.get("group_seq"),
            is_bundle=row_dict.get("is_bundle"),
        )

        items.append(
            InspectionWorkInstructionTargetOut(
                lot_id=row_dict["lot_id"],
                lot_no=row_dict["lot_no"],
                outsource_work_group_id=row_dict["outsource_work_group_id"],
                outsource_work_group_item_id=row_dict["outsource_work_group_item_id"],
                bundle_no=bundle_no,
                product_code=row_dict.get("product_code"),
                product_name=row_dict.get("product_name"),
                partner_name=row_dict.get("partner_name"),
                lot_qty=row_dict["lot_qty"],
                due_date=row_dict.get("due_date"),
                memo=row_dict.get("memo"),
            )
        )

    return InspectionWorkInstructionTargetListOut(items=items)


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
            InspectionSchedule.outsource_work_group_id,
            InspectionSchedule.outsource_work_group_item_id,
            OutsourceWorkGroup.group_seq,
            OutsourceWorkGroup.is_bundle,
            OutsourceWorkGroup.status.label("outsource_work_group_status"),
            OutsourceWorkInstruction.instruction_no,
            InspectionSchedule.memo,
        )
        .select_from(InspectionSchedule)
        .join(Lot, Lot.lot_id == InspectionSchedule.lot_id)
        .join(OrderLine, OrderLine.order_line_id == Lot.order_line_id)
        .join(Partner, Partner.partner_id == OrderLine.partner_id)
        .join(Product, Product.product_id == OrderLine.product_id)
        .outerjoin(
            OutsourceWorkGroup,
            OutsourceWorkGroup.outsource_work_group_id
            == InspectionSchedule.outsource_work_group_id,
        )
        .outerjoin(
            OutsourceWorkInstruction,
            OutsourceWorkInstruction.outsource_work_instruction_id
            == OutsourceWorkGroup.outsource_work_instruction_id,
        )
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

        row_dict["bundle_no"] = _build_inspection_bundle_no_from_values(
            instruction_no=row_dict.get("instruction_no"),
            outsource_work_group_id=row_dict.get("outsource_work_group_id"),
            group_seq=row_dict.get("group_seq"),
            is_bundle=row_dict.get("is_bundle"),
        )

        row_dict["diecut_status"] = _to_diecut_status_label(
            row_dict.get("outsource_work_group_status")
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