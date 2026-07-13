from __future__ import annotations

from collections.abc import Callable

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.defect_type import DefectType
from app.models.inspection_defect import InspectionDefect
from app.models.inspection_defect_attachment import InspectionDefectAttachment
from app.models.inspection_result import InspectionResult
from app.models.inspection_schedule import InspectionSchedule
from app.models.lot import Lot
from app.models.order_line import OrderLine
from app.models.order_line_plan_history import OrderLinePlanHistory
from app.models.outsource_work_group import OutsourceWorkGroup
from app.models.outsource_work_group_item import OutsourceWorkGroupItem
from app.models.outsource_work_instruction import OutsourceWorkInstruction
from app.models.partner import Partner
from app.models.product import Product
from app.models.product_inventory import ProductInventory
from app.schemas.lot import (
    LotTraceBasicOut,
    LotTraceDefectAttachmentOut,
    LotTraceDetailOut,
    LotTraceInspectionDefectOut,
    LotTraceInspectionOut,
    LotTraceOutsourceWorkOut,
    LotTraceProductOrderOut,
    LotTraceProgressOut,
)


def get_lot_trace_detail_for_lot(
    db: Session,
    lot_id: int,
    *,
    attachment_content_url_builder: Callable[[int], str] | None = None,
) -> LotTraceDetailOut:
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
    latest_plan_history = _get_latest_plan_history(db, order_line.order_line_id)
    current_stock_qty = _get_current_stock_qty(db, product.product_id)
    parent_lot_no = _get_parent_lot_no(db, lot)
    outsource_works = _build_outsource_works(db, lot_id)
    inspection = _build_inspection(
        db,
        lot_id,
        attachment_content_url_builder=attachment_content_url_builder,
    )

    return LotTraceDetailOut(
        progress=_build_lot_trace_progress(
            outsource_works=outsource_works,
            inspection=inspection,
        ),
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


def _get_latest_plan_history(
    db: Session,
    order_line_id: int,
) -> OrderLinePlanHistory | None:
    return (
        db.execute(
            select(OrderLinePlanHistory)
            .where(OrderLinePlanHistory.order_line_id == order_line_id)
            .order_by(
                OrderLinePlanHistory.created_at.desc(),
                OrderLinePlanHistory.plan_history_id.desc(),
            )
            .limit(1)
        )
        .scalar_one_or_none()
    )


def _get_current_stock_qty(db: Session, product_id: int) -> int:
    current_stock_qty = db.execute(
        select(ProductInventory.current_qty).where(
            ProductInventory.product_id == product_id
        )
    ).scalar_one_or_none()

    return int(current_stock_qty or 0)


def _get_parent_lot_no(db: Session, lot: Lot) -> str | None:
    if not lot.parent_lot_id:
        return None

    parent_lot = db.get(Lot, lot.parent_lot_id)
    return parent_lot.lot_no if parent_lot else None


def _build_outsource_works(
    db: Session,
    lot_id: int,
) -> list[LotTraceOutsourceWorkOut]:
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

    return outsource_works


def _build_inspection(
    db: Session,
    lot_id: int,
    *,
    attachment_content_url_builder: Callable[[int], str] | None,
) -> LotTraceInspectionOut | None:
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

    if completed_inspection_rows:
        inspection_schedule, inspection_result = completed_inspection_rows[-1]
    elif latest_schedule_row is not None:
        inspection_schedule, inspection_result = latest_schedule_row
    else:
        return None

    result_rows_for_totals = completed_inspection_rows

    if not result_rows_for_totals and inspection_result is not None:
        result_rows_for_totals = [(inspection_schedule, inspection_result)]

    result_ids = [
        result.inspection_result_id
        for _, result in result_rows_for_totals
        if result is not None
    ]

    defects = _build_inspection_defects(
        db,
        result_ids,
        attachment_content_url_builder=attachment_content_url_builder,
    )

    return LotTraceInspectionOut(
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
        inspected_qty=_sum_result_qty(result_rows_for_totals, "inspected_qty"),
        good_qty=_sum_result_qty(result_rows_for_totals, "good_qty"),
        defect_qty=_sum_result_qty(result_rows_for_totals, "defect_qty"),
        defect_ship_qty=_sum_result_qty(result_rows_for_totals, "defect_ship_qty"),
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


def _sum_result_qty(
    result_rows: list[tuple[InspectionSchedule, InspectionResult]],
    attr_name: str,
) -> int | None:
    if not result_rows:
        return None

    return sum(
        int(getattr(result, attr_name) or 0)
        for _, result in result_rows
        if result is not None
    )


def _build_inspection_defects(
    db: Session,
    result_ids: list[int],
    *,
    attachment_content_url_builder: Callable[[int], str] | None,
) -> list[LotTraceInspectionDefectOut]:
    if not result_ids:
        return []

    defect_rows = (
        db.execute(
            select(InspectionDefect, DefectType)
            .join(
                DefectType,
                DefectType.defect_type_id == InspectionDefect.defect_type_id,
            )
            .where(InspectionDefect.inspection_result_id.in_(result_ids))
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
    attachments_by_defect_id = _load_attachments_by_defect_id(db, defect_ids)

    return [
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
                    image_url=(
                        attachment_content_url_builder(
                            attachment.inspection_defect_attachment_id
                        )
                        if attachment_content_url_builder
                        else None
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


def _load_attachments_by_defect_id(
    db: Session,
    defect_ids: list[int],
) -> dict[int, list[InspectionDefectAttachment]]:
    if not defect_ids:
        return {}

    attachment_rows = (
        db.execute(
            select(InspectionDefectAttachment)
            .where(InspectionDefectAttachment.inspection_defect_id.in_(defect_ids))
            .order_by(InspectionDefectAttachment.inspection_defect_attachment_id)
        )
        .scalars()
        .all()
    )

    attachments_by_defect_id: dict[int, list[InspectionDefectAttachment]] = {}
    for attachment in attachment_rows:
        attachments_by_defect_id.setdefault(
            attachment.inspection_defect_id,
            [],
        ).append(attachment)

    return attachments_by_defect_id


def _format_defect_type_name(defect_type: DefectType | None) -> str | None:
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
