from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from fastapi import Request
from sqlalchemy import desc, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.crud.lot import lot_crud
from app.db.session import get_db
from app.models.lot import Lot
from app.models.lot_step import LotStep
from app.models.order_line import OrderLine
from app.models.partner import Partner
from app.models.process import Process
from app.models.product import Product
from app.models.routing_template_step import RoutingTemplateStep
from app.models.defect_type import DefectType
from app.models.inspection_defect import InspectionDefect
from app.models.product_inventory import ProductInventory
from app.models.inspection_result import InspectionResult
from app.models.inspection_schedule import InspectionSchedule
from app.models.inspection_defect_attachment import InspectionDefectAttachment
from app.models.outsource_work_group import OutsourceWorkGroup
from app.models.outsource_work_group_item import OutsourceWorkGroupItem
from app.models.outsource_work_instruction import OutsourceWorkInstruction
from app.models.order_line_plan_history import OrderLinePlanHistory

from app.schemas.lot import (
    LotCreate,
    LotOut,
    LotDetailOut,
    LotListOut,
    LotTraceDetailOut,
    LotTraceProgressOut,
    LotTraceBasicOut,
    LotTraceProductOrderOut,
    LotTraceOutsourceWorkOut,
    LotTraceInspectionOut,
    LotTraceInspectionDefectOut,
    LotTraceDefectAttachmentOut,
    PageMeta,

)

router = APIRouter(prefix="/lots", tags=["Lot"])


def _get_lot_month_code(value: date) -> str:
    month_codes = {
        1: "A",
        2: "B",
        3: "C",
        4: "D",
        5: "E",
        6: "F",
        7: "G",
        8: "H",
        9: "I",
        10: "J",
        11: "K",
        12: "L",
    }
    return month_codes[value.month]


def _generate_lot_no(db: Session, created_date: date, e_fixed: str = "E") -> str:
    yy = f"{created_date.year % 100:02d}"
    dd = f"{created_date.day:02d}"
    month_code = _get_lot_month_code(created_date)
    fixed_code = (e_fixed or "E").strip().upper()
    prefix = f"CT{yy}{month_code}{dd}{fixed_code}"
    legacy_prefix = f"CT{yy}{created_date.month:02d}{dd}0"

    existing_lot_nos = db.execute(
        select(Lot.lot_no)
        .where(or_(Lot.lot_no.like(f"{prefix}%"), Lot.lot_no.like(f"{legacy_prefix}%")))
        .order_by(desc(Lot.lot_no))
    ).scalars().all()

    max_seq = 0
    for lot_no in existing_lot_nos:
        try:
            max_seq = max(max_seq, int(lot_no[-2:]))
        except ValueError:
            continue

    nn = max_seq + 1

    if nn > 99:
        raise HTTPException(status_code=409, detail="LOT sequence exceeded for the day (NN > 99)")

    return f"{prefix}{nn:02d}"


def _ensure_order_line(db: Session, order_line_id: int) -> OrderLine:
    ol = db.get(OrderLine, order_line_id)
    if not ol or not ol.is_active:
        raise HTTPException(status_code=404, detail="OrderLine not found or inactive")
    return ol


def _ensure_parent_lot(db: Session, parent_lot_id: int) -> Lot:
    parent = db.get(Lot, parent_lot_id)
    if not parent:
        raise HTTPException(status_code=404, detail="Parent LOT not found")
    return parent


def _create_lot_steps_from_routing(db: Session, lot_id: int, routing_template_id: int) -> None:
    steps = db.execute(
        select(RoutingTemplateStep)
        .where(
            RoutingTemplateStep.routing_template_id == routing_template_id,
            RoutingTemplateStep.is_active == True,  # noqa: E712
        )
        .order_by(RoutingTemplateStep.step_seq.asc())
    ).scalars().all()

    if not steps:
        raise HTTPException(status_code=409, detail="RoutingTemplate has no active steps")

    process_ids = [s.process_id for s in steps]
    procs = db.execute(select(Process).where(Process.process_id.in_(process_ids))).scalars().all()
    process_map = {p.process_id: p for p in procs}

    for s in steps:
        p = process_map.get(s.process_id)
        if not p:
            raise HTTPException(status_code=409, detail=f"Process not found for process_id={s.process_id}")

        db.add(
            LotStep(
                lot_id=lot_id,
                step_seq=s.step_seq,
                process_id=s.process_id,
                process_code=p.process_code,
                process_name=p.process_name,
                process_type=s.default_process_type,
                status="WAITING",
            )
        )


def _normalize_optional_str(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    value = value.strip()
    return value or None

def _format_defect_type_name(defect_type) -> str | None:
    if defect_type is None:
        return None

    category1 = (defect_type.category1_name or "").strip()
    category2 = (defect_type.category2_name or "").strip()

    if category1 and category2:
        return f"{category1} / {category2}"

    if category2:
        return category2

    if category1:
        return category1

    return defect_type.code



def _validate_material_fields(payload: LotCreate):
    material_lot_no = _normalize_optional_str(payload.material_lot_no)
    material_used_qty = payload.material_used_qty
    material_sheet_count = payload.material_sheet_count

    has_lot_no = material_lot_no is not None
    has_used_qty = material_used_qty is not None
    has_sheet_count = material_sheet_count is not None

    if has_lot_no and not has_used_qty:
        raise HTTPException(status_code=409, detail="material_used_qty is required when material_lot_no is provided")

    if has_used_qty and not has_lot_no:
        raise HTTPException(status_code=409, detail="material_lot_no is required when material_used_qty is provided")

    if has_sheet_count and not has_lot_no:
        raise HTTPException(status_code=409, detail="material_lot_no is required when material_sheet_count is provided")

    return material_lot_no, material_used_qty, material_sheet_count


def _has_normal_lot(db: Session, order_line_id: int) -> bool:
    existing = (
        db.execute(
            select(Lot.lot_id)
            .where(
                Lot.order_line_id == order_line_id,
                Lot.parent_lot_id.is_(None),
            )
            .limit(1)
        )
        .scalar_one_or_none()
    )
    return existing is not None


@router.post("", response_model=LotDetailOut, status_code=http_status.HTTP_201_CREATED)
def create_lot(payload: LotCreate, db: Session = Depends(get_db)):
    ol = _ensure_order_line(db, payload.order_line_id)

    product = db.get(Product, ol.product_id)
    if not product or not product.is_active:
        raise HTTPException(status_code=409, detail="Product not found or inactive")

    created_date = payload.created_date or date.today()
    parent_lot_id_in = payload.parent_lot_id or None
    lot_qty = int(payload.lot_qty)

    if parent_lot_id_in is None:
        raise HTTPException(
            status_code=409,
            detail="Manual LOT creation is allowed for rework LOT only",
        )

    material_lot_no, material_used_qty, material_sheet_count = _validate_material_fields(payload)

    parent = _ensure_parent_lot(db, parent_lot_id_in)

    if parent.order_line_id != ol.order_line_id:
        raise HTTPException(status_code=409, detail="Parent LOT must belong to same OrderLine")

    if parent.parent_lot_id is not None:
        raise HTTPException(status_code=409, detail="Parent LOT must be a primary LOT")

    if parent.status not in ("DONE", "CANCELED"):
        raise HTTPException(
            status_code=409,
            detail="Rework LOT can only be created when parent LOT is DONE or CANCELED",
        )

    if ol.status == "DONE":
        ol.status = "CLOSED"

    parent_lot_id = parent.lot_id

    for _ in range(3):
        lot_no = _generate_lot_no(db, created_date, e_fixed="E")
        lot = Lot(
            lot_no=lot_no,
            order_line_id=ol.order_line_id,
            product_id=ol.product_id,
            parent_lot_id=parent_lot_id,
            lot_qty=lot_qty,
            uom=ol.uom,
            material_lot_no=material_lot_no,
            material_used_qty=material_used_qty,
            material_sheet_count=material_sheet_count,
            created_date=created_date,
            due_date=ol.due_date,
            memo=payload.memo,
            status="WAITING",
        )

        try:
            lot_crud.create(db, lot)
            _create_lot_steps_from_routing(db, lot.lot_id, product.routing_template_id)
            db.commit()
            db.refresh(lot)
            break
        except IntegrityError:
            db.rollback()
            continue
    else:
        raise HTTPException(status_code=409, detail="Failed to generate unique lot_no (retry exceeded)")

    out = LotDetailOut.model_validate(lot, from_attributes=True)
    partner = db.get(Partner, ol.partner_id)
    out.order_no = ol.order_no
    out.line_no = ol.line_no
    out.partner_id = ol.partner_id
    out.partner_name = partner.name if partner else None
    out.product_code = product.product_code
    out.product_name = product.product_name
    out.steps = [s for s in lot.steps]
    return out


@router.get("", response_model=LotListOut)
def list_lots(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    q: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    order_line_id: Optional[int] = Query(None),
    product_id: Optional[int] = Query(None),
    partner_id: Optional[int] = Query(None),
    due_date_from: Optional[date] = Query(None),
    due_date_to: Optional[date] = Query(None),
    created_date_from: Optional[date] = Query(None),
    created_date_to: Optional[date] = Query(None),
    inspection_schedule_registered: Optional[bool] = Query(None),
    sort: Optional[str] = Query(None),
):
    items, total = lot_crud.list_with_joins(
        db,
        page=page,
        size=size,
        status=status,
        q=q,
        order_line_id=order_line_id,
        product_id=product_id,
        partner_id=partner_id,
        due_date_from=due_date_from,
        due_date_to=due_date_to,
        created_date_from=created_date_from,
        created_date_to=created_date_to,
        inspection_schedule_registered=inspection_schedule_registered,
        sort=sort,
    )

    return LotListOut(
        items=[LotOut(**x) for x in items],
        meta=PageMeta(page=page, size=size, total=total),
    )

def _to_plan_type_display(plan_type: str | None) -> str | None:
    if not plan_type:
        return None

    mapping = {
        "AUTO_PRODUCTION": "자동 생산",
        "AUTO_STOCK_SHIP": "재고 출고",
        "PARTIAL_STOCK_ONLY_CLOSE": "재고만 출고 후 종료",
        "PARTIAL_STOCK_PLUS_PRODUCTION": "부분재고 + 부족분 생산",
        "STOCK_REPLENISHMENT": "재고비축 생산",
    }

    return mapping.get(plan_type, plan_type)

def _build_lot_trace_progress(
    outsource_works: list[LotTraceOutsourceWorkOut],
    inspection: LotTraceInspectionOut | None,
) -> LotTraceProgressOut:
    outsource_instruction_created = len(outsource_works) > 0

    outsource_work_done = any(
        x.work_done_sheet_qty is not None
        or x.status in ("WORK_DONE", "SHIPPED")
        for x in outsource_works
    )

    inspection_done = (
        inspection is not None
        and inspection.inspection_result_id is not None
        and inspection.schedule_status in ("DONE", "PARTIAL_DONE")
    )

    return LotTraceProgressOut(
        lot_created=True,
        outsource_instruction_created=outsource_instruction_created,
        outsource_work_done=outsource_work_done,
        inspection_done=inspection_done,
    )

@router.get("/{lot_id}/detail", response_model=LotTraceDetailOut)
def get_lot_trace_detail(
    lot_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    row = (
        db.execute(
            select(Lot, OrderLine, Product, Partner)
            .join(OrderLine, OrderLine.order_line_id == Lot.order_line_id)
            .join(Product, Product.product_id == Lot.product_id)
            .join(Partner, Partner.partner_id == OrderLine.partner_id)
            .where(Lot.lot_id == lot_id)
        )
        .one_or_none()
    )

    if row is None:
        raise HTTPException(status_code=404, detail="LOT not found")

    lot, order_line, product, partner = row

    latest_plan_history = (
        db.execute(
            select(OrderLinePlanHistory)
            .where(OrderLinePlanHistory.order_line_id == order_line.order_line_id)
            .order_by(
                OrderLinePlanHistory.created_at.desc(),
                OrderLinePlanHistory.plan_history_id.desc(),
            )
            .limit(1)
        )
        .scalar_one_or_none()
    )


    current_stock_qty = db.execute(
        select(ProductInventory.current_qty)
        .where(ProductInventory.product_id == product.product_id)
    ).scalar_one_or_none()

    current_stock_qty = int(current_stock_qty or 0)

    parent_lot_no = None

    if lot.parent_lot_id:
        parent_lot = db.get(Lot, lot.parent_lot_id)
        parent_lot_no = parent_lot.lot_no if parent_lot else None

    outsource_rows = (
        db.execute(
            select(
                OutsourceWorkGroup,
                OutsourceWorkGroupItem,
                OutsourceWorkInstruction,
            )
            .join(
                OutsourceWorkGroupItem,
                OutsourceWorkGroupItem.outsource_work_group_id
                == OutsourceWorkGroup.outsource_work_group_id,
            )
            .join(
                OutsourceWorkInstruction,
                OutsourceWorkInstruction.outsource_work_instruction_id
                == OutsourceWorkGroup.outsource_work_instruction_id,
            )
            .where(OutsourceWorkGroupItem.lot_id == lot_id)
            .order_by(
                OutsourceWorkInstruction.instruction_date.desc(),
                OutsourceWorkInstruction.instruction_no.desc(),
                OutsourceWorkGroup.group_seq.asc(),
                OutsourceWorkGroupItem.outsource_work_group_item_id.asc(),
            )
        )
        .all()
    )

    outsource_works: list[LotTraceOutsourceWorkOut] = []

    for work_group, work_group_item, instruction in outsource_rows:
        group_expected_output_qty = (
            int(work_group.sheet_qty) * int(work_group.sheet_cut_count)
        )

        confirmed_outsource_qty = None

        if work_group.work_done_sheet_qty is not None:
            confirmed_outsource_qty = (
                int(work_group.work_done_sheet_qty)
                * int(work_group.sheet_cut_count)
            )

        outsource_works.append(
            LotTraceOutsourceWorkOut(
                outsource_work_group_id=work_group.outsource_work_group_id,
                outsource_work_group_item_id=work_group_item.outsource_work_group_item_id,
                outsource_work_instruction_id=instruction.outsource_work_instruction_id,
                instruction_no=instruction.instruction_no,
                instruction_date=instruction.instruction_date,
                process_type=work_group.process_type,
                group_seq=work_group.group_seq,
                is_bundle=work_group.is_bundle,
                fabric_lot_no=work_group.fabric_lot_no,
                length_m=work_group.length_m,
                sheet_qty=work_group.sheet_qty,
                sheet_cut_count=work_group.sheet_cut_count,
                cuts_per_sheet=work_group_item.cuts_per_sheet,
                expected_output_qty=work_group_item.expected_output_qty,
                group_expected_output_qty=group_expected_output_qty,
                work_done_sheet_qty=work_group.work_done_sheet_qty,
                confirmed_outsource_qty=confirmed_outsource_qty,
                status=work_group.status,
                vendor_received_at=work_group.vendor_received_at,
                work_done_at=work_group.work_done_at,
                shipped_at=work_group.shipped_at,
                remark=work_group.remark,
                work_done_remark=work_group.work_done_remark,
            )
        )

    latest_schedule_row = (
        db.execute(
            select(InspectionSchedule, InspectionResult)
            .join(
                InspectionResult,
                InspectionResult.inspection_schedule_id
                == InspectionSchedule.inspection_schedule_id,
                isouter=True,
            )
            .where(InspectionSchedule.lot_id == lot_id)
            .order_by(
                InspectionSchedule.inspection_date.desc(),
                InspectionSchedule.inspection_schedule_id.desc(),
            )
            .limit(1)
        )
        .one_or_none()
    )

    completed_inspection_rows = (
        db.execute(
            select(InspectionSchedule, InspectionResult)
            .join(
                InspectionResult,
                InspectionResult.inspection_schedule_id
                == InspectionSchedule.inspection_schedule_id,
            )
            .where(
                InspectionSchedule.lot_id == lot_id,
                InspectionSchedule.status.in_(("PARTIAL_DONE", "DONE")),
            )
            .order_by(
                InspectionSchedule.inspection_date.asc(),
                InspectionSchedule.inspection_schedule_id.asc(),
            )
        )
        .all()
    )

    inspection: LotTraceInspectionOut | None = None

    if completed_inspection_rows:
        inspection_schedule, inspection_result = completed_inspection_rows[-1]
    elif latest_schedule_row is not None:
        inspection_schedule, inspection_result = latest_schedule_row
    else:
        inspection_schedule = None
        inspection_result = None

    if inspection_schedule is not None:
        defects: list[LotTraceInspectionDefectOut] = []
        result_rows_for_totals = completed_inspection_rows

        if not result_rows_for_totals and inspection_result is not None:
            result_rows_for_totals = [(inspection_schedule, inspection_result)]

        result_ids = [
            result.inspection_result_id
            for _, result in result_rows_for_totals
            if result is not None
        ]

        total_inspected_qty = (
            sum((result.inspected_qty or 0) for _, result in result_rows_for_totals)
            if result_rows_for_totals
            else None
        )
        total_good_qty = (
            sum((result.good_qty or 0) for _, result in result_rows_for_totals)
            if result_rows_for_totals
            else None
        )
        total_defect_qty = (
            sum((result.defect_qty or 0) for _, result in result_rows_for_totals)
            if result_rows_for_totals
            else None
        )
        total_defect_ship_qty = (
            sum((result.defect_ship_qty or 0) for _, result in result_rows_for_totals)
            if result_rows_for_totals
            else None
        )

        if result_ids:
            defect_rows = (
                db.execute(
                    select(InspectionDefect, DefectType)
                    .join(
                        DefectType,
                        DefectType.defect_type_id
                        == InspectionDefect.defect_type_id,
                    )
                    .where(
                        InspectionDefect.inspection_result_id
                        .in_(result_ids)
                    )
                    .order_by(
                        InspectionDefect.inspection_result_id.asc(),
                        InspectionDefect.inspection_defect_id.asc(),
                    )
                )
                .all()
            )

            defect_ids = [
                inspection_defect.inspection_defect_id
                for inspection_defect, _ in defect_rows
            ]

            attachment_rows = []

            if defect_ids:
                attachment_rows = (
                    db.query(InspectionDefectAttachment)
                    .filter(InspectionDefectAttachment.inspection_defect_id.in_(defect_ids))
                    .order_by(InspectionDefectAttachment.inspection_defect_attachment_id)
                    .all()
                )

            attachments_by_defect_id = {}

            for attachment in attachment_rows:
                attachments_by_defect_id.setdefault(
                    attachment.inspection_defect_id,
                    [],
                ).append(attachment)

            defects = [
                LotTraceInspectionDefectOut(
                    inspection_defect_id=inspection_defect.inspection_defect_id,
                    defect_type_id=inspection_defect.defect_type_id,
                    defect_type_code=defect_type.code,
                    defect_type_name=_format_defect_type_name(defect_type),
                    defect_qty=inspection_defect.defect_qty,
                    disposition=inspection_defect.disposition,
                    memo=inspection_defect.memo,
                    attachments=[
                        LotTraceDefectAttachmentOut(
                            inspection_defect_attachment_id=attachment.inspection_defect_attachment_id,
                            file_uri=attachment.file_uri,
                            file_name=attachment.file_name,
                            mime_type=attachment.mime_type,
                            memo=attachment.memo,
                            image_url=str(
                                request.url_for(
                                    "get_result_attachment_content",
                                    attachment_id=attachment.inspection_defect_attachment_id,
                                )
                            ),
                        )
                        for attachment in attachments_by_defect_id.get(
                            inspection_defect.inspection_defect_id,
                            [],
                        )
                    ],
                )
                for inspection_defect, defect_type in defect_rows
            ]

        inspection = LotTraceInspectionOut(
            inspection_schedule_id=inspection_schedule.inspection_schedule_id,
            inspection_date=inspection_schedule.inspection_date,
            schedule_status=inspection_schedule.status,
            received_at=inspection_schedule.received_at,
            started_at=inspection_schedule.started_at,
            finished_at=inspection_schedule.finished_at,
            inspection_result_id=(
                inspection_result.inspection_result_id
                if inspection_result
                else None
            ),
            inspected_qty=total_inspected_qty,
            good_qty=total_good_qty,
            defect_qty=total_defect_qty,
            defect_ship_qty=total_defect_ship_qty,
            is_partial=inspection_result.is_partial if inspection_result else None,
            next_inspection_date=(
                inspection_result.next_inspection_date
                if inspection_result
                else None
            ),
            partial_reason=(
                inspection_result.partial_reason
                if inspection_result
                else None
            ),
            memo=inspection_result.memo if inspection_result else None,
            created_by=inspection_result.created_by if inspection_result else None,
            result_created_at=(
                inspection_result.created_at
                if inspection_result
                else None
            ),
            defects=defects,
        )

    progress = _build_lot_trace_progress(
        outsource_works=outsource_works,
        inspection=inspection,
    )

    return LotTraceDetailOut(
        progress=progress,
        lot_basic=LotTraceBasicOut(
            lot_id=lot.lot_id,
            lot_no=lot.lot_no,
            status=lot.status,
            is_rework=lot.parent_lot_id is not None,
            parent_lot_id=lot.parent_lot_id,
            parent_lot_no=parent_lot_no,
            lot_qty=lot.lot_qty,
            uom=lot.uom,
            created_date=lot.created_date,
            due_date=lot.due_date,
            memo=lot.memo,
        ),
        product_order=LotTraceProductOrderOut(
        order_line_id=order_line.order_line_id,
        order_no=order_line.order_no,
        line_no=order_line.line_no,
        partner_id=partner.partner_id,
        partner_name=partner.name,
        product_id=product.product_id,
        product_code=product.product_code,
        product_name=product.product_name,
        product_spec=product.product_spec,
        panel_width_mm=product.panel_width_mm,
        panel_length_mm=product.panel_length_mm,
        cut_qty_per_panel=product.cut_qty_per_panel,
        current_stock_qty=current_stock_qty,
        order_qty=order_line.order_qty,
        order_date=order_line.order_date,
        due_date=order_line.due_date,
        memo=order_line.memo,
        plan_type=latest_plan_history.plan_type if latest_plan_history else None,
        plan_type_display=(
            _to_plan_type_display(latest_plan_history.plan_type)
            if latest_plan_history
            else None
        ),
        plan_ship_target_qty=(
            latest_plan_history.ship_target_qty
            if latest_plan_history
            else None
        ),
        plan_available_inventory_qty=(
            latest_plan_history.available_inventory_qty
            if latest_plan_history
            else None
        ),
        plan_stock_ship_qty=(
            latest_plan_history.stock_ship_qty
            if latest_plan_history
            else None
        ),
        plan_production_qty=(
            latest_plan_history.production_qty
            if latest_plan_history
            else None
        ),
        plan_is_short_close=(
            latest_plan_history.is_short_close
            if latest_plan_history
            else None
        ),
        ),
        outsource_works=outsource_works,
        inspection=inspection,
    )


@router.get("/{lot_id}", response_model=LotDetailOut)
def get_lot(lot_id: int, db: Session = Depends(get_db)):
    lot = lot_crud.get(db, lot_id)
    if not lot:
        raise HTTPException(status_code=404, detail="LOT not found")

    ol = db.get(OrderLine, lot.order_line_id)
    product = db.get(Product, lot.product_id)
    partner = db.get(Partner, ol.partner_id) if ol else None

    out = LotDetailOut.model_validate(lot, from_attributes=True)

    if ol:
        out.order_no = ol.order_no
        out.line_no = ol.line_no
        out.partner_id = ol.partner_id
        out.partner_name = partner.name if partner else None

    if product:
        out.product_code = product.product_code
        out.product_name = product.product_name

    out.steps = [s for s in lot.steps]
    return out

