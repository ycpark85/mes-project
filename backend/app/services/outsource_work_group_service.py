from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.models.inspection_schedule import InspectionSchedule
from app.models.outsource_work_group import OutsourceWorkGroup
from app.models.outsource_work_group_change_log import OutsourceWorkGroupChangeLog
from app.models.outsource_work_group_item import OutsourceWorkGroupItem
from app.models.outsource_work_group_raw_material_allocation import (
    OutsourceWorkGroupRawMaterialAllocation,
)
from app.models.outsource_work_group_self_use_sheet_allocation import (
    OutsourceWorkGroupSelfUseSheetAllocation,
)
from app.models.outsource_work_group_self_use_sheet_source_snapshot import (
    OutsourceWorkGroupSelfUseSheetSourceSnapshot,
)
from app.models.outsource_work_instruction_item import OutsourceWorkInstructionItem
from app.models.raw_material_inventory import RawMaterialInventory
from app.models.raw_material_inventory_lot import RawMaterialInventoryLot
from app.models.raw_material_inventory_movement import RawMaterialInventoryMovement
from app.models.raw_material import RawMaterial
from app.models.raw_material_location import RawMaterialLocation
from app.models.self_use_sheet_inventory_balance import SelfUseSheetInventoryBalance
from app.models.self_use_sheet_inventory_lot import SelfUseSheetInventoryLot
from app.models.self_use_sheet_inventory_movement import SelfUseSheetInventoryMovement
from app.models.self_use_sheet_raw_material_allocation import SelfUseSheetRawMaterialAllocation
from app.models.lot import Lot
from app.models.product import Product
from app.schemas.outsource_work_instruction import (
    OutsourceWorkGroupCancelIn,
    OutsourceWorkGroupUpdateIn,
    OutsourceWorkInstructionRawMaterialAllocationCreate,
    OutsourceWorkInstructionSelfUseSheetAllocationCreate,
)
from app.services.outsource_work_instruction_query import (
    OUTSOURCE_WORK_GROUP_STATUS_CANCELED,
    get_cancel_block_reason,
    get_update_block_reason,
)
from app.services.production_daily_query import refresh_order_line_snapshots_for_work_groups


def update_work_group(
    db: Session,
    outsource_work_group_id: int,
    payload: OutsourceWorkGroupUpdateIn,
) -> OutsourceWorkGroup:
    work_group = _get_work_group_for_update(db, outsource_work_group_id)

    update_block_reason = get_update_block_reason(db, work_group)
    if update_block_reason is not None:
        raise HTTPException(status_code=409, detail=update_block_reason)
    if work_group.input_source_type == "SELF_USE_SHEET":
        raise HTTPException(
            status_code=409,
            detail="Self-use sheet work groups cannot be edited. Cancel and create a new work instruction.",
        )

    reason = payload.reason.strip()
    if not reason:
        raise HTTPException(status_code=422, detail="Update reason is required")

    required_qty = _q2(payload.length_m)
    allocated_qty = _q2(
        sum((allocation.qty for allocation in payload.raw_material_allocations), Decimal("0"))
    )

    if required_qty != allocated_qty:
        raise HTTPException(
            status_code=409,
            detail="Raw material allocation total must match length_m",
        )

    before_data = _build_work_group_change_snapshot(db, work_group)

    reverse_raw_material_allocations(
        db,
        work_group,
        reason,
        source_type="OUTSOURCE_WORK_GROUP_UPDATE",
    )

    work_group.sheet_qty = payload.sheet_qty
    work_group.length_m = required_qty
    work_group.sheet_cut_count = payload.sheet_cut_count
    work_group.fabric_lot_no = (
        payload.fabric_lot_no.strip()
        if payload.fabric_lot_no and payload.fabric_lot_no.strip()
        else None
    )
    work_group.remark = payload.remark.strip() if payload.remark and payload.remark.strip() else None

    group_items = (
        db.execute(
            select(OutsourceWorkGroupItem)
            .where(
                OutsourceWorkGroupItem.outsource_work_group_id
                == work_group.outsource_work_group_id
            )
            .with_for_update()
        )
        .scalars()
        .all()
    )

    for group_item in group_items:
        group_item.cuts_per_sheet = payload.sheet_cut_count
        group_item.expected_output_qty = payload.sheet_qty * payload.sheet_cut_count

    consume_raw_material_allocations(
        db=db,
        work_group=work_group,
        allocations=payload.raw_material_allocations,
    )

    after_data = _build_work_group_change_snapshot(db, work_group)
    db.add(
        OutsourceWorkGroupChangeLog(
            outsource_work_group_id=work_group.outsource_work_group_id,
            action_type="UPDATE",
            reason=reason,
            before_data=before_data,
            after_data=after_data,
        )
    )

    refresh_order_line_snapshots_for_work_groups(db, [work_group.outsource_work_group_id])
    db.flush()
    return work_group


def cancel_work_group(
    db: Session,
    outsource_work_group_id: int,
    payload: OutsourceWorkGroupCancelIn,
) -> OutsourceWorkGroup:
    work_group = _get_work_group_for_update(db, outsource_work_group_id)

    cancel_block_reason = get_cancel_block_reason(db, work_group)
    if cancel_block_reason is not None:
        raise HTTPException(status_code=409, detail=cancel_block_reason)

    reason = payload.reason.strip()
    if not reason:
        raise HTTPException(status_code=422, detail="Cancel reason is required")

    reverse_raw_material_allocations(db, work_group, reason)
    reverse_self_use_sheet_allocations(db, work_group, reason)
    _cancel_linked_inspection_schedules(db, work_group)

    work_group.status = OUTSOURCE_WORK_GROUP_STATUS_CANCELED
    work_group.canceled_at = utc_now()
    work_group.canceled_reason = reason

    group_lot_ids = [
        row[0]
        for row in db.execute(
            select(OutsourceWorkGroupItem.lot_id).where(
                OutsourceWorkGroupItem.outsource_work_group_id
                == work_group.outsource_work_group_id
            )
        ).all()
    ]

    if group_lot_ids:
        instruction_items = (
            db.execute(
                select(OutsourceWorkInstructionItem)
                .where(
                    OutsourceWorkInstructionItem.outsource_work_instruction_id
                    == work_group.outsource_work_instruction_id,
                    OutsourceWorkInstructionItem.lot_id.in_(group_lot_ids),
                    OutsourceWorkInstructionItem.process_type == work_group.process_type,
                    OutsourceWorkInstructionItem.is_active.is_(True),
                )
                .with_for_update()
            )
            .scalars()
            .all()
        )

        for instruction_item in instruction_items:
            instruction_item.is_active = False

    refresh_order_line_snapshots_for_work_groups(db, [work_group.outsource_work_group_id])
    db.flush()
    return work_group


def _cancel_linked_inspection_schedules(
    db: Session,
    work_group: OutsourceWorkGroup,
) -> None:
    schedules = (
        db.execute(
            select(InspectionSchedule)
            .where(
                InspectionSchedule.outsource_work_group_id
                == work_group.outsource_work_group_id,
                InspectionSchedule.status.in_(("WAITING", "RECEIVED")),
            )
            .with_for_update()
        )
        .scalars()
        .all()
    )

    for schedule in schedules:
        schedule.status = "CANCELED"


def consume_raw_material_allocations(
    db: Session,
    work_group: OutsourceWorkGroup,
    allocations: list[OutsourceWorkInstructionRawMaterialAllocationCreate],
) -> None:
    if not allocations:
        return

    for allocation_payload in allocations:
        qty = _q2(allocation_payload.qty)

        if qty <= 0:
            raise HTTPException(
                status_code=422,
                detail="Raw material allocation qty must be greater than 0",
            )

        inventory_lot = (
            db.execute(
                select(RawMaterialInventoryLot)
                .where(
                    RawMaterialInventoryLot.raw_material_inventory_lot_id
                    == allocation_payload.raw_material_inventory_lot_id
                )
                .with_for_update()
            )
            .scalar_one_or_none()
        )

        if inventory_lot is None:
            raise HTTPException(status_code=404, detail="Raw material inventory lot not found")

        inventory = (
            db.execute(
                select(RawMaterialInventory)
                .where(
                    RawMaterialInventory.raw_material_id == inventory_lot.raw_material_id,
                    RawMaterialInventory.raw_material_location_id
                    == inventory_lot.raw_material_location_id,
                )
                .with_for_update()
            )
            .scalar_one_or_none()
        )

        if inventory is None:
            raise HTTPException(
                status_code=409,
                detail="Raw material location inventory not found",
            )

        if inventory_lot.current_qty < qty or inventory.current_qty < qty:
            raise HTTPException(status_code=409, detail="Raw material inventory is insufficient")

        amount_snapshot = _amount(qty, inventory_lot.unit_cost)
        memo = (
            allocation_payload.memo.strip()
            if allocation_payload.memo and allocation_payload.memo.strip()
            else None
        )
        allocation = OutsourceWorkGroupRawMaterialAllocation(
            outsource_work_group_id=work_group.outsource_work_group_id,
            raw_material_id=inventory_lot.raw_material_id,
            raw_material_location_id=inventory_lot.raw_material_location_id,
            raw_material_inventory_lot_id=inventory_lot.raw_material_inventory_lot_id,
            lot_no=inventory_lot.lot_no,
            qty=qty,
            unit_cost_snapshot=inventory_lot.unit_cost,
            amount_snapshot=amount_snapshot,
            status="CONSUMED",
            memo=memo,
        )
        db.add(allocation)
        db.flush()

        inventory_lot.current_qty = _q2(inventory_lot.current_qty - qty)
        inventory.current_qty = _q2(inventory.current_qty - qty)

        movement = RawMaterialInventoryMovement(
            raw_material_id=inventory_lot.raw_material_id,
            raw_material_location_id=inventory_lot.raw_material_location_id,
            raw_material_inventory_lot_id=inventory_lot.raw_material_inventory_lot_id,
            lot_no=inventory_lot.lot_no,
            movement_type="CONSUME_OUT",
            qty=-qty,
            balance_after=inventory.current_qty,
            unit_cost_snapshot=inventory_lot.unit_cost,
            amount_snapshot=amount_snapshot,
            source_type="OUTSOURCE_WORK_GROUP_RAW_MATERIAL_ALLOCATION",
            source_id=allocation.outsource_work_group_raw_material_allocation_id,
            memo=memo,
        )
        db.add(movement)
        db.flush()

        allocation.raw_material_inventory_movement_id = movement.raw_material_inventory_movement_id


def consume_self_use_sheet_allocations(
    db: Session,
    work_group: OutsourceWorkGroup,
    allocations: list[OutsourceWorkInstructionSelfUseSheetAllocationCreate],
) -> None:
    if not allocations:
        raise HTTPException(status_code=422, detail="Self-use sheet allocation is required")
    allocated_qty = sum(item.qty for item in allocations)
    if allocated_qty != work_group.sheet_qty:
        raise HTTPException(status_code=409, detail="Self-use sheet allocation total must match sheet_qty")

    product_dimensions = (
        db.execute(
            select(Product.panel_width_mm, Product.panel_length_mm)
            .join(Lot, Lot.product_id == Product.product_id)
            .join(OutsourceWorkGroupItem, OutsourceWorkGroupItem.lot_id == Lot.lot_id)
            .where(OutsourceWorkGroupItem.outsource_work_group_id == work_group.outsource_work_group_id)
        )
        .all()
    )

    for payload in allocations:
        sheet_lot = (
            db.execute(
                select(SelfUseSheetInventoryLot)
                .where(
                    SelfUseSheetInventoryLot.self_use_sheet_inventory_lot_id
                    == payload.self_use_sheet_inventory_lot_id
                )
                .with_for_update()
            )
            .scalar_one_or_none()
        )
        if sheet_lot is None:
            raise HTTPException(status_code=404, detail="Self-use sheet inventory LOT not found")
        if sheet_lot.status != "AVAILABLE" or sheet_lot.current_qty < payload.qty:
            raise HTTPException(status_code=409, detail="Self-use sheet inventory is insufficient")
        for panel_width_mm, panel_length_mm in product_dimensions:
            if panel_width_mm is None or panel_length_mm is None:
                raise HTTPException(status_code=409, detail="Product panel dimensions are required for self-use sheet allocation")
            panel_width = Decimal(panel_width_mm)
            panel_length = Decimal(panel_length_mm)
            fits_without_rotation = (
                panel_width <= sheet_lot.cut_width_mm
                and panel_length <= sheet_lot.cut_length_mm
            )
            fits_with_rotation = (
                panel_width <= sheet_lot.cut_length_mm
                and panel_length <= sheet_lot.cut_width_mm
            )
            if not fits_without_rotation and not fits_with_rotation:
                raise HTTPException(
                    status_code=409,
                    detail="Self-use sheet dimensions cannot contain the selected product panel",
                )

        location_balance = (
            db.execute(
                select(SelfUseSheetInventoryBalance)
                .where(
                    SelfUseSheetInventoryBalance.self_use_sheet_inventory_lot_id
                    == sheet_lot.self_use_sheet_inventory_lot_id,
                    SelfUseSheetInventoryBalance.raw_material_location_id == payload.source_location_id,
                )
                .with_for_update()
            )
            .scalar_one_or_none()
        )
        if location_balance is None or location_balance.current_qty < payload.qty:
            raise HTTPException(status_code=409, detail="Self-use sheet inventory is insufficient at the selected location")

        memo = payload.memo.strip() if payload.memo and payload.memo.strip() else None
        amount_snapshot = _amount(Decimal(payload.qty), sheet_lot.unit_cost) or Decimal("0")
        allocation = OutsourceWorkGroupSelfUseSheetAllocation(
            outsource_work_group_id=work_group.outsource_work_group_id,
            self_use_sheet_inventory_lot_id=sheet_lot.self_use_sheet_inventory_lot_id,
            source_location_id=payload.source_location_id,
            sheet_lot_no=sheet_lot.sheet_lot_no,
            qty=payload.qty,
            unit_cost_snapshot=sheet_lot.unit_cost,
            amount_snapshot=amount_snapshot,
            status="CONSUMED",
            memo=memo,
        )
        db.add(allocation)
        db.flush()

        sheet_lot.current_qty -= payload.qty
        location_balance.current_qty -= payload.qty
        sheet_lot.status = "DEPLETED" if sheet_lot.current_qty == 0 else "AVAILABLE"
        sheet_lot.version += 1
        movement = SelfUseSheetInventoryMovement(
            self_use_sheet_inventory_lot_id=sheet_lot.self_use_sheet_inventory_lot_id,
            movement_type="WORK_USE_OUT",
            raw_material_location_id=payload.source_location_id,
            qty=-payload.qty,
            balance_after=sheet_lot.current_qty,
            location_balance_after=location_balance.current_qty,
            unit_cost_snapshot=sheet_lot.unit_cost,
            amount_snapshot=amount_snapshot,
            source_type="OUTSOURCE_WORK_GROUP_SELF_USE_SHEET_ALLOCATION",
            source_id=allocation.outsource_work_group_self_use_sheet_allocation_id,
            memo=memo,
            created_by="system",
        )
        db.add(movement)
        db.flush()
        allocation.inventory_movement_id = movement.self_use_sheet_inventory_movement_id

        source_rows = (
            db.execute(
                select(SelfUseSheetRawMaterialAllocation, RawMaterial, RawMaterialLocation)
                .join(RawMaterial, RawMaterial.raw_material_id == SelfUseSheetRawMaterialAllocation.raw_material_id)
                .join(
                    RawMaterialLocation,
                    RawMaterialLocation.raw_material_location_id
                    == SelfUseSheetRawMaterialAllocation.source_location_id,
                )
                .where(
                    SelfUseSheetRawMaterialAllocation.self_use_sheet_job_id
                    == sheet_lot.self_use_sheet_job_id
                )
                .order_by(SelfUseSheetRawMaterialAllocation.self_use_sheet_raw_material_allocation_id.asc())
            )
            .all()
        )
        for source, raw_material, source_location in source_rows:
            db.add(
                OutsourceWorkGroupSelfUseSheetSourceSnapshot(
                    self_use_sheet_allocation_id=allocation.outsource_work_group_self_use_sheet_allocation_id,
                    self_use_sheet_raw_material_allocation_id=source.self_use_sheet_raw_material_allocation_id,
                    original_inventory_lot_id=source.original_inventory_lot_id,
                    raw_material_id=source.raw_material_id,
                    raw_material_code_snapshot=raw_material.material_code,
                    raw_material_name_snapshot=raw_material.material_name,
                    raw_material_lot_no_snapshot=source.lot_no,
                    source_location_name_snapshot=source_location.location_name,
                    actual_consumed_qty_snapshot=source.actual_consumed_qty or Decimal("0"),
                    unit_cost_snapshot=source.unit_cost_snapshot or Decimal("0"),
                    amount_snapshot=source.amount_snapshot or Decimal("0"),
                )
            )


def reverse_self_use_sheet_allocations(
    db: Session,
    work_group: OutsourceWorkGroup,
    reason: str | None,
) -> None:
    allocations = (
        db.execute(
            select(OutsourceWorkGroupSelfUseSheetAllocation)
            .where(
                OutsourceWorkGroupSelfUseSheetAllocation.outsource_work_group_id
                == work_group.outsource_work_group_id,
                OutsourceWorkGroupSelfUseSheetAllocation.status == "CONSUMED",
            )
            .with_for_update()
        )
        .scalars()
        .all()
    )
    for allocation in allocations:
        sheet_lot = (
            db.execute(
                select(SelfUseSheetInventoryLot)
                .where(
                    SelfUseSheetInventoryLot.self_use_sheet_inventory_lot_id
                    == allocation.self_use_sheet_inventory_lot_id
                )
                .with_for_update()
            )
            .scalar_one()
        )
        if sheet_lot.status == "CANCELED":
            raise HTTPException(status_code=409, detail="Canceled self-use sheet inventory cannot be restored")
        balance = (
            db.execute(
                select(SelfUseSheetInventoryBalance)
                .where(
                    SelfUseSheetInventoryBalance.self_use_sheet_inventory_lot_id
                    == allocation.self_use_sheet_inventory_lot_id,
                    SelfUseSheetInventoryBalance.raw_material_location_id == allocation.source_location_id,
                )
                .with_for_update()
            )
            .scalar_one_or_none()
        )
        if balance is None:
            balance = SelfUseSheetInventoryBalance(
                self_use_sheet_inventory_lot_id=allocation.self_use_sheet_inventory_lot_id,
                raw_material_location_id=allocation.source_location_id,
                current_qty=0,
            )
            db.add(balance)
            db.flush()
        sheet_lot.current_qty += allocation.qty
        balance.current_qty += allocation.qty
        sheet_lot.status = "AVAILABLE"
        sheet_lot.version += 1
        db.add(
            SelfUseSheetInventoryMovement(
                self_use_sheet_inventory_lot_id=allocation.self_use_sheet_inventory_lot_id,
                movement_type="WORK_USE_REVERSE",
                raw_material_location_id=allocation.source_location_id,
                qty=allocation.qty,
                balance_after=sheet_lot.current_qty,
                location_balance_after=balance.current_qty,
                unit_cost_snapshot=allocation.unit_cost_snapshot,
                amount_snapshot=allocation.amount_snapshot,
                source_movement_id=allocation.inventory_movement_id,
                source_type="OUTSOURCE_WORK_GROUP_CANCEL",
                source_id=allocation.outsource_work_group_self_use_sheet_allocation_id,
                memo=reason,
                created_by="system",
            )
        )
        allocation.status = "REVERSED"


def reverse_raw_material_allocations(
    db: Session,
    work_group: OutsourceWorkGroup,
    reason: str | None,
    source_type: str = "OUTSOURCE_WORK_GROUP_CANCEL",
) -> None:
    allocations = (
        db.execute(
            select(OutsourceWorkGroupRawMaterialAllocation)
            .where(
                OutsourceWorkGroupRawMaterialAllocation.outsource_work_group_id
                == work_group.outsource_work_group_id,
                OutsourceWorkGroupRawMaterialAllocation.status == "CONSUMED",
            )
            .with_for_update()
        )
        .scalars()
        .all()
    )

    for allocation in allocations:
        qty = _q2(allocation.qty)
        inventory = _get_or_create_raw_material_inventory_for_reverse(
            db,
            raw_material_id=allocation.raw_material_id,
            raw_material_location_id=allocation.raw_material_location_id,
        )
        inventory_lot = _get_or_create_raw_material_lot_for_reverse(db, allocation)

        inventory.current_qty = _q2(inventory.current_qty + qty)
        inventory_lot.current_qty = _q2(inventory_lot.current_qty + qty)

        movement = RawMaterialInventoryMovement(
            raw_material_id=allocation.raw_material_id,
            raw_material_location_id=allocation.raw_material_location_id,
            raw_material_inventory_lot_id=inventory_lot.raw_material_inventory_lot_id,
            lot_no=allocation.lot_no,
            movement_type="CONSUME_REVERSE",
            qty=qty,
            balance_after=inventory.current_qty,
            unit_cost_snapshot=allocation.unit_cost_snapshot,
            amount_snapshot=allocation.amount_snapshot,
            source_type=source_type,
            source_id=allocation.outsource_work_group_raw_material_allocation_id,
            memo=reason,
        )
        db.add(movement)
        allocation.status = "REVERSED"
        db.flush()


def _get_work_group_for_update(
    db: Session,
    outsource_work_group_id: int,
) -> OutsourceWorkGroup:
    work_group = (
        db.execute(
            select(OutsourceWorkGroup)
            .where(OutsourceWorkGroup.outsource_work_group_id == outsource_work_group_id)
            .with_for_update()
        )
        .scalar_one_or_none()
    )

    if work_group is None:
        raise HTTPException(status_code=404, detail="Outsource work group not found")

    return work_group


def _get_or_create_raw_material_inventory_for_reverse(
    db: Session,
    raw_material_id: int,
    raw_material_location_id: int,
) -> RawMaterialInventory:
    inventory = (
        db.execute(
            select(RawMaterialInventory)
            .where(
                RawMaterialInventory.raw_material_id == raw_material_id,
                RawMaterialInventory.raw_material_location_id == raw_material_location_id,
            )
            .with_for_update()
        )
        .scalar_one_or_none()
    )

    if inventory is not None:
        return inventory

    inventory = RawMaterialInventory(
        raw_material_id=raw_material_id,
        raw_material_location_id=raw_material_location_id,
        current_qty=Decimal("0"),
    )
    db.add(inventory)
    db.flush()
    return inventory


def _get_or_create_raw_material_lot_for_reverse(
    db: Session,
    allocation: OutsourceWorkGroupRawMaterialAllocation,
) -> RawMaterialInventoryLot:
    inventory_lot: RawMaterialInventoryLot | None = None

    if allocation.raw_material_inventory_lot_id is not None:
        inventory_lot = (
            db.execute(
                select(RawMaterialInventoryLot)
                .where(
                    RawMaterialInventoryLot.raw_material_inventory_lot_id
                    == allocation.raw_material_inventory_lot_id
                )
                .with_for_update()
            )
            .scalar_one_or_none()
        )

    if inventory_lot is None:
        inventory_lot = (
            db.execute(
                select(RawMaterialInventoryLot)
                .where(
                    RawMaterialInventoryLot.raw_material_id == allocation.raw_material_id,
                    RawMaterialInventoryLot.raw_material_location_id
                    == allocation.raw_material_location_id,
                    RawMaterialInventoryLot.lot_no == allocation.lot_no,
                )
                .with_for_update()
            )
            .scalar_one_or_none()
        )

    if inventory_lot is not None:
        return inventory_lot

    inventory_lot = RawMaterialInventoryLot(
        raw_material_id=allocation.raw_material_id,
        raw_material_location_id=allocation.raw_material_location_id,
        lot_no=allocation.lot_no,
        current_qty=Decimal("0"),
        unit_cost=allocation.unit_cost_snapshot,
    )
    db.add(inventory_lot)
    db.flush()
    return inventory_lot


def _build_work_group_change_snapshot(
    db: Session,
    work_group: OutsourceWorkGroup,
) -> dict:
    group_items = (
        db.execute(
            select(OutsourceWorkGroupItem)
            .where(
                OutsourceWorkGroupItem.outsource_work_group_id
                == work_group.outsource_work_group_id
            )
            .order_by(OutsourceWorkGroupItem.outsource_work_group_item_id.asc())
        )
        .scalars()
        .all()
    )
    allocations = (
        db.execute(
            select(OutsourceWorkGroupRawMaterialAllocation)
            .where(
                OutsourceWorkGroupRawMaterialAllocation.outsource_work_group_id
                == work_group.outsource_work_group_id,
                OutsourceWorkGroupRawMaterialAllocation.status == "CONSUMED",
            )
            .order_by(
                OutsourceWorkGroupRawMaterialAllocation.outsource_work_group_raw_material_allocation_id.asc()
            )
        )
        .scalars()
        .all()
    )

    return {
        "outsource_work_group_id": work_group.outsource_work_group_id,
        "sheet_qty": work_group.sheet_qty,
        "length_m": _json_value(work_group.length_m),
        "sheet_cut_count": work_group.sheet_cut_count,
        "fabric_lot_no": work_group.fabric_lot_no,
        "remark": work_group.remark,
        "items": [
            {
                "outsource_work_group_item_id": item.outsource_work_group_item_id,
                "lot_id": item.lot_id,
                "cuts_per_sheet": item.cuts_per_sheet,
                "expected_output_qty": item.expected_output_qty,
            }
            for item in group_items
        ],
        "raw_material_allocations": [
            {
                "outsource_work_group_raw_material_allocation_id": allocation.outsource_work_group_raw_material_allocation_id,
                "raw_material_inventory_lot_id": allocation.raw_material_inventory_lot_id,
                "lot_no": allocation.lot_no,
                "qty": _json_value(allocation.qty),
                "unit_cost_snapshot": _json_value(allocation.unit_cost_snapshot),
                "amount_snapshot": _json_value(allocation.amount_snapshot),
                "status": allocation.status,
            }
            for allocation in allocations
        ],
    }


def _json_value(value):
    if isinstance(value, Decimal):
        return str(_q2(value))
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _q2(value: Decimal | int | float | str | None) -> Decimal:
    return Decimal(value or 0).quantize(Decimal("0.01"))


def _amount(qty: Decimal, unit_cost: Decimal | None) -> Decimal | None:
    if unit_cost is None:
        return None

    return (qty * unit_cost).quantize(Decimal("0.01"))
