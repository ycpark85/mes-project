from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.orm import Session

from app.models.inspection_certificate import InspectionCertificate
from app.models.inspection_defect import InspectionDefect
from app.models.inspection_defect_attachment import InspectionDefectAttachment
from app.models.inspection_result import InspectionResult
from app.models.inspection_schedule import InspectionSchedule
from app.models.lot import Lot
from app.models.lot_step import LotStep
from app.models.order_line import OrderLine
from app.models.order_line_plan_history import OrderLinePlanHistory
from app.models.outsource_purchase_order_item import OutsourcePurchaseOrderItem
from app.models.outsource_work_group_item import OutsourceWorkGroupItem
from app.models.outsource_work_instruction_item import OutsourceWorkInstructionItem
from app.models.product_inventory_movement import ProductInventoryMovement
from app.models.shipment_coa import ShipmentCoa
from app.models.shipment_line import ShipmentLine


def delete_order_line_group(db: Session, order_line_id: int) -> dict[str, Any]:
    selected_order_line = (
        db.execute(
            select(OrderLine)
            .where(OrderLine.order_line_id == order_line_id)
            .with_for_update()
        )
        .scalar_one_or_none()
    )

    if not selected_order_line or not selected_order_line.is_active:
        raise HTTPException(status_code=404, detail="OrderLine not found")

    order_no = selected_order_line.order_no
    order_lines = _load_order_lines_for_order_no(db, order_no)
    order_line_ids = [x.order_line_id for x in order_lines]
    if not order_line_ids:
        raise HTTPException(status_code=404, detail="OrderLine not found")

    lots = _load_lots(db, order_line_ids)
    lot_ids = [x.lot_id for x in lots]
    schedules = _load_inspection_schedules(db, lot_ids)
    inspection_schedule_ids = [x.inspection_schedule_id for x in schedules]
    results = _load_inspection_results(db, inspection_schedule_ids)
    inspection_result_ids = [x.inspection_result_id for x in results]
    shipment_lines = _load_shipment_lines(db, order_line_ids, lot_ids, inspection_result_ids)
    shipment_line_ids = [x.shipment_line_id for x in shipment_lines]

    blockers = _collect_delete_blockers(
        db,
        order_no=order_no,
        order_line_ids=order_line_ids,
        lots=lots,
        lot_ids=lot_ids,
        schedules=schedules,
        inspection_schedule_ids=inspection_schedule_ids,
        inspection_result_ids=inspection_result_ids,
        shipment_lines=shipment_lines,
        shipment_line_ids=shipment_line_ids,
    )
    if blockers:
        raise HTTPException(
            status_code=409,
            detail=(
                f"수주번호 {order_no}는 운영 데이터가 있어 삭제할 수 없습니다. "
                f"삭제 차단 항목: {', '.join(blockers)}"
            ),
        )

    defects = _load_inspection_defects(db, inspection_result_ids)
    defect_ids = [x.inspection_defect_id for x in defects]

    _delete_rows_by_ids(
        db,
        InspectionDefectAttachment,
        InspectionDefectAttachment.inspection_defect_id,
        defect_ids,
    )
    _delete_rows_by_ids(
        db,
        InspectionDefect,
        InspectionDefect.inspection_defect_id,
        defect_ids,
    )
    _delete_rows_by_ids(
        db,
        ShipmentLine,
        ShipmentLine.shipment_line_id,
        shipment_line_ids,
    )
    _delete_rows_by_ids(
        db,
        InspectionResult,
        InspectionResult.inspection_result_id,
        inspection_result_ids,
    )
    _delete_rows_by_ids(
        db,
        InspectionSchedule,
        InspectionSchedule.inspection_schedule_id,
        inspection_schedule_ids,
    )

    if lot_ids:
        db.execute(
            update(Lot)
            .where(Lot.parent_lot_id.in_(lot_ids))
            .values(parent_lot_id=None)
        )

    _delete_rows_by_ids(db, LotStep, LotStep.lot_id, lot_ids)
    _delete_rows_by_ids(db, Lot, Lot.lot_id, lot_ids)
    _delete_rows_by_ids(
        db,
        OrderLinePlanHistory,
        OrderLinePlanHistory.order_line_id,
        order_line_ids,
    )
    _delete_rows_by_ids(
        db,
        OrderLine,
        OrderLine.order_line_id,
        order_line_ids,
    )

    return {
        "success": True,
        "order_no": order_no,
        "deleted_order_line_count": len(order_line_ids),
        "deleted_lot_count": len(lot_ids),
        "deleted_shipment_line_count": len(shipment_line_ids),
    }


def _load_order_lines_for_order_no(db: Session, order_no: str) -> list[OrderLine]:
    return (
        db.execute(
            select(OrderLine)
            .where(OrderLine.order_no == order_no)
            .with_for_update()
        )
        .scalars()
        .all()
    )


def _load_lots(db: Session, order_line_ids: list[int]) -> list[Lot]:
    return (
        db.execute(
            select(Lot)
            .where(Lot.order_line_id.in_(order_line_ids))
            .with_for_update()
        )
        .scalars()
        .all()
    )


def _load_inspection_schedules(db: Session, lot_ids: list[int]) -> list[InspectionSchedule]:
    if not lot_ids:
        return []

    return (
        db.execute(
            select(InspectionSchedule)
            .where(InspectionSchedule.lot_id.in_(lot_ids))
            .with_for_update()
        )
        .scalars()
        .all()
    )


def _load_inspection_results(db: Session, inspection_schedule_ids: list[int]) -> list[InspectionResult]:
    if not inspection_schedule_ids:
        return []

    return (
        db.execute(
            select(InspectionResult)
            .where(InspectionResult.inspection_schedule_id.in_(inspection_schedule_ids))
            .with_for_update()
        )
        .scalars()
        .all()
    )


def _load_shipment_lines(
    db: Session,
    order_line_ids: list[int],
    lot_ids: list[int],
    inspection_result_ids: list[int],
) -> list[ShipmentLine]:
    shipment_conditions = [ShipmentLine.order_line_id.in_(order_line_ids)]
    if lot_ids:
        shipment_conditions.append(ShipmentLine.lot_id.in_(lot_ids))
    if inspection_result_ids:
        shipment_conditions.append(ShipmentLine.inspection_result_id.in_(inspection_result_ids))

    return (
        db.execute(
            select(ShipmentLine)
            .where(or_(*shipment_conditions))
            .with_for_update()
        )
        .scalars()
        .all()
    )


def _collect_delete_blockers(
    db: Session,
    *,
    order_no: str,
    order_line_ids: list[int],
    lots: list[Lot],
    lot_ids: list[int],
    schedules: list[InspectionSchedule],
    inspection_schedule_ids: list[int],
    inspection_result_ids: list[int],
    shipment_lines: list[ShipmentLine],
    shipment_line_ids: list[int],
) -> list[str]:
    blockers: list[str] = []

    progressed_lot_count = len([x for x in lots if x.status not in {"WAITING", "CANCELED"}])
    if progressed_lot_count > 0:
        blockers.append(f"진행/완료 LOT {progressed_lot_count}건")

    progressed_schedule_count = len([x for x in schedules if x.status not in {"WAITING", "CANCELED"}])
    if progressed_schedule_count > 0:
        blockers.append(f"진행/완료 검수스케줄 {progressed_schedule_count}건")

    done_shipment_count = len([x for x in shipment_lines if x.status == "DONE"])
    if done_shipment_count > 0:
        blockers.append(f"출하확정 데이터 {done_shipment_count}건")

    _append_inventory_movement_blocker(
        db,
        blockers,
        order_line_ids=order_line_ids,
        inspection_schedule_ids=inspection_schedule_ids,
        inspection_result_ids=inspection_result_ids,
        shipment_line_ids=shipment_line_ids,
    )
    _append_shipment_coa_blocker(db, blockers, order_line_ids)
    _append_certificate_blocker(db, blockers, lot_ids, inspection_result_ids)
    _append_outsource_blocker(db, blockers, lot_ids)

    return blockers


def _append_inventory_movement_blocker(
    db: Session,
    blockers: list[str],
    *,
    order_line_ids: list[int],
    inspection_schedule_ids: list[int],
    inspection_result_ids: list[int],
    shipment_line_ids: list[int],
) -> None:
    movement_conditions = [ProductInventoryMovement.order_line_id.in_(order_line_ids)]
    if inspection_result_ids:
        movement_conditions.append(ProductInventoryMovement.inspection_result_id.in_(inspection_result_ids))
    if inspection_schedule_ids:
        movement_conditions.append(ProductInventoryMovement.inspection_schedule_id.in_(inspection_schedule_ids))
    if shipment_line_ids:
        movement_conditions.append(
            and_(
                ProductInventoryMovement.source_type == "SHIPMENT_LINE",
                ProductInventoryMovement.source_id.in_(shipment_line_ids),
            )
        )

    inventory_movement_count = _count_rows(
        db,
        ProductInventoryMovement,
        or_(*movement_conditions),
    )
    if inventory_movement_count > 0:
        blockers.append(f"재고 입출고 이력 {inventory_movement_count}건")


def _append_shipment_coa_blocker(
    db: Session,
    blockers: list[str],
    order_line_ids: list[int],
) -> None:
    shipment_coa_count = _count_rows(
        db,
        ShipmentCoa,
        ShipmentCoa.order_line_id.in_(order_line_ids),
    )
    if shipment_coa_count > 0:
        blockers.append(f"출고 COA {shipment_coa_count}건")


def _append_certificate_blocker(
    db: Session,
    blockers: list[str],
    lot_ids: list[int],
    inspection_result_ids: list[int],
) -> None:
    certificate_conditions = []
    if lot_ids:
        certificate_conditions.append(InspectionCertificate.lot_id.in_(lot_ids))
    if inspection_result_ids:
        certificate_conditions.append(InspectionCertificate.basis_inspection_result_id.in_(inspection_result_ids))

    if not certificate_conditions:
        return

    certificate_count = _count_rows(
        db,
        InspectionCertificate,
        or_(*certificate_conditions),
    )
    if certificate_count > 0:
        blockers.append(f"검사성적서 {certificate_count}건")


def _append_outsource_blocker(
    db: Session,
    blockers: list[str],
    lot_ids: list[int],
) -> None:
    if not lot_ids:
        return

    outsource_work_instruction_count = _count_rows(
        db,
        OutsourceWorkInstructionItem,
        OutsourceWorkInstructionItem.lot_id.in_(lot_ids),
    )
    outsource_work_group_count = _count_rows(
        db,
        OutsourceWorkGroupItem,
        OutsourceWorkGroupItem.lot_id.in_(lot_ids),
    )
    outsource_purchase_order_count = _count_rows(
        db,
        OutsourcePurchaseOrderItem,
        OutsourcePurchaseOrderItem.lot_id.in_(lot_ids),
    )

    outsource_count = (
        outsource_work_instruction_count
        + outsource_work_group_count
        + outsource_purchase_order_count
    )
    if outsource_count > 0:
        blockers.append(f"외주 연결 데이터 {outsource_count}건")


def _load_inspection_defects(db: Session, inspection_result_ids: list[int]) -> list[InspectionDefect]:
    if not inspection_result_ids:
        return []

    return (
        db.execute(
            select(InspectionDefect).where(
                InspectionDefect.inspection_result_id.in_(inspection_result_ids)
            )
        )
        .scalars()
        .all()
    )


def _count_rows(db: Session, model, *conditions) -> int:
    stmt = select(func.count()).select_from(model)
    if conditions:
        stmt = stmt.where(*conditions)
    return int(db.execute(stmt).scalar_one() or 0)


def _delete_rows_by_ids(db: Session, model, id_column, ids: list[int]) -> None:
    if not ids:
        return

    db.execute(delete(model).where(id_column.in_(ids)))
