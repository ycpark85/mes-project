from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.models.partner import Partner
from app.models.raw_material import RawMaterial
from app.models.raw_material_inventory import RawMaterialInventory
from app.models.raw_material_inventory_lot import RawMaterialInventoryLot
from app.models.raw_material_inventory_movement import RawMaterialInventoryMovement
from app.models.raw_material_location import RawMaterialLocation
from app.models.self_use_sheet_inventory_balance import SelfUseSheetInventoryBalance
from app.models.self_use_sheet_inventory_lot import SelfUseSheetInventoryLot
from app.models.self_use_sheet_inventory_movement import SelfUseSheetInventoryMovement
from app.models.self_use_sheet_job import SelfUseSheetJob
from app.models.self_use_sheet_raw_material_allocation import SelfUseSheetRawMaterialAllocation
from app.schemas.self_use_sheet import (
    SelfUseSheetInventoryLotOut,
    SelfUseSheetJobCancel,
    SelfUseSheetJobComplete,
    SelfUseSheetJobCreate,
    SelfUseSheetJobOut,
    SelfUseSheetJobStart,
    SelfUseSheetTransferIn,
    SelfUseSheetUseIn,
    SelfUseSheetUseReverseIn,
)
from app.schemas.raw_material import RawMaterialLocationCreate
from app.services.raw_material_master_service import create_raw_material_location_in_session
from app.services.self_use_sheet_query import (
    get_self_use_sheet_inventory_lot,
    get_self_use_sheet_job,
    list_self_use_sheet_inventory,
    list_self_use_sheet_jobs,
    list_self_use_sheet_movements,
)


def _q2(value: Decimal | int) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _q4(value: Decimal | int) -> Decimal:
    return Decimal(value).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def _money(qty: Decimal | int, unit_cost: Decimal | None) -> Decimal:
    if unit_cost is None:
        return Decimal("0.00")
    return (abs(_q2(qty)) * _q4(unit_cost)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_self_use_sheet_output_qty(
    *,
    input_length_m: Decimal,
    cut_width_mm: Decimal,
    cut_length_mm: Decimal,
) -> int:
    input_length_m = Decimal(input_length_m)
    cut_width_mm = Decimal(cut_width_mm)
    cut_length_mm = Decimal(cut_length_mm)
    if input_length_m <= 0 or cut_width_mm <= 0 or cut_length_mm <= 0:
        return 0
    if cut_width_mm != cut_width_mm.to_integral_value() or cut_length_mm != cut_length_mm.to_integral_value():
        return 0

    usable_length_m = input_length_m * Decimal("0.98")
    cut_length_m = cut_length_mm / Decimal("1000")
    raw_qty = usable_length_m / cut_length_m
    rounded_qty = (raw_qty / Decimal("5")).quantize(
        Decimal("1"),
        rounding=ROUND_HALF_UP,
    ) * Decimal("5")
    width_multiplier = 2 if cut_width_mm in {Decimal("250"), Decimal("300")} else 1
    return max(0, int(rounded_qty) * width_multiplier)


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _new_number(prefix: str) -> str:
    return f"{prefix}-{utc_now():%Y%m%d}-{uuid4().hex[:8].upper()}"


def _require_version(actual: int, expected: int) -> None:
    if actual != expected:
        raise HTTPException(
            status_code=409,
            detail="The record was changed by another user. Reload and try again.",
        )


def _ensure_outsource_vendor_location(db: Session, partner_id: int) -> RawMaterialLocation:
    partner = (
        db.execute(
            select(Partner)
            .where(Partner.partner_id == partner_id)
            .with_for_update()
        )
        .scalar_one_or_none()
    )
    if partner is None or not partner.is_active or partner.partner_type != "VENDOR":
        raise HTTPException(status_code=422, detail="Active vendor partner is required")

    location = (
        db.execute(
            select(RawMaterialLocation)
            .where(
                RawMaterialLocation.location_type == "OUTSOURCE_VENDOR",
                RawMaterialLocation.partner_id == partner_id,
            )
            .order_by(
                RawMaterialLocation.is_active.desc(),
                RawMaterialLocation.raw_material_location_id.asc(),
            )
        )
        .scalars()
        .first()
    )
    if location is not None:
        if not location.is_active:
            location.is_active = True
            db.flush()
        return location

    created = create_raw_material_location_in_session(
        db,
        RawMaterialLocationCreate(
            location_name=f"{partner.name} 외주 원자재",
            location_type="OUTSOURCE_VENDOR",
            partner_id=partner_id,
            is_active=True,
            memo="자가사용 시트지 외주 출고 위치 자동 생성",
        ),
    )
    return db.get(RawMaterialLocation, created.raw_material_location_id)


def _require_job(db: Session, job_id: int, *, lock: bool = False) -> SelfUseSheetJob:
    statement = select(SelfUseSheetJob).where(SelfUseSheetJob.self_use_sheet_job_id == job_id)
    if lock:
        statement = statement.with_for_update()
    job = db.execute(statement).scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Self-use sheet job not found")
    return job


def _get_sheet_balance(
    db: Session,
    *,
    lot_id: int,
    location_id: int,
    lock: bool = False,
    create: bool = False,
) -> SelfUseSheetInventoryBalance | None:
    statement = select(SelfUseSheetInventoryBalance).where(
        SelfUseSheetInventoryBalance.self_use_sheet_inventory_lot_id == lot_id,
        SelfUseSheetInventoryBalance.raw_material_location_id == location_id,
    )
    if lock:
        statement = statement.with_for_update()
    balance = db.execute(statement).scalar_one_or_none()
    if balance is None and create:
        balance = SelfUseSheetInventoryBalance(
            self_use_sheet_inventory_lot_id=lot_id,
            raw_material_location_id=location_id,
            current_qty=0,
        )
        db.add(balance)
        db.flush()
    return balance


def _resolve_usage_balance(
    db: Session,
    *,
    lot_id: int,
    location_id: int | None,
) -> SelfUseSheetInventoryBalance:
    if location_id is not None:
        balance = _get_sheet_balance(
            db,
            lot_id=lot_id,
            location_id=location_id,
            lock=True,
        )
        if balance is None:
            raise HTTPException(status_code=409, detail="Self-use sheet inventory does not exist at the selected location")
        return balance

    balances = (
        db.execute(
            select(SelfUseSheetInventoryBalance)
            .where(
                SelfUseSheetInventoryBalance.self_use_sheet_inventory_lot_id == lot_id,
                SelfUseSheetInventoryBalance.current_qty > 0,
            )
            .order_by(SelfUseSheetInventoryBalance.self_use_sheet_inventory_balance_id.asc())
            .with_for_update()
        )
        .scalars()
        .all()
    )
    if len(balances) != 1:
        raise HTTPException(status_code=422, detail="Select the self-use sheet inventory location")
    return balances[0]


def _get_inventory(
    db: Session,
    *,
    raw_material_id: int,
    location_id: int,
) -> RawMaterialInventory:
    inventory = (
        db.execute(
            select(RawMaterialInventory)
            .where(
                RawMaterialInventory.raw_material_id == raw_material_id,
                RawMaterialInventory.raw_material_location_id == location_id,
            )
            .with_for_update()
        )
        .scalar_one_or_none()
    )
    if inventory is None:
        inventory = RawMaterialInventory(
            raw_material_id=raw_material_id,
            raw_material_location_id=location_id,
            current_qty=Decimal("0"),
        )
        db.add(inventory)
        db.flush()
    return inventory


def _get_or_create_raw_material_lot(
    db: Session,
    *,
    raw_material_id: int,
    location_id: int,
    lot_no: str,
    unit_cost: Decimal | None,
    received_at: date | None,
) -> RawMaterialInventoryLot:
    inventory_lot = (
        db.execute(
            select(RawMaterialInventoryLot)
            .where(
                RawMaterialInventoryLot.raw_material_id == raw_material_id,
                RawMaterialInventoryLot.raw_material_location_id == location_id,
                func.upper(RawMaterialInventoryLot.lot_no) == lot_no.upper(),
            )
            .with_for_update()
        )
        .scalar_one_or_none()
    )
    if inventory_lot is None:
        inventory_lot = RawMaterialInventoryLot(
            raw_material_id=raw_material_id,
            raw_material_location_id=location_id,
            lot_no=lot_no,
            current_qty=Decimal("0"),
            unit_cost=unit_cost,
            received_at=received_at,
        )
        db.add(inventory_lot)
        db.flush()
    return inventory_lot


def _transfer_raw_material(
    db: Session,
    *,
    source_lot: RawMaterialInventoryLot,
    to_location_id: int,
    qty: Decimal,
    job: SelfUseSheetJob,
    memo: str,
) -> tuple[RawMaterialInventoryLot, str]:
    qty = _q2(qty)
    if source_lot.raw_material_location_id == to_location_id:
        return source_lot, ""
    if source_lot.current_qty < qty:
        raise HTTPException(status_code=409, detail=f"Raw material LOT {source_lot.lot_no} inventory is insufficient")

    source_inventory = _get_inventory(
        db,
        raw_material_id=source_lot.raw_material_id,
        location_id=source_lot.raw_material_location_id,
    )
    target_inventory = _get_inventory(
        db,
        raw_material_id=source_lot.raw_material_id,
        location_id=to_location_id,
    )
    target_lot = _get_or_create_raw_material_lot(
        db,
        raw_material_id=source_lot.raw_material_id,
        location_id=to_location_id,
        lot_no=source_lot.lot_no,
        unit_cost=source_lot.unit_cost,
        received_at=source_lot.received_at,
    )
    transfer_key = f"SUS-TR-{uuid4().hex[:16].upper()}"
    source_lot.current_qty = _q2(source_lot.current_qty - qty)
    source_inventory.current_qty = _q2(source_inventory.current_qty - qty)
    target_lot.current_qty = _q2(target_lot.current_qty + qty)
    target_inventory.current_qty = _q2(target_inventory.current_qty + qty)
    db.add_all(
        [
            RawMaterialInventoryMovement(
                raw_material_id=source_lot.raw_material_id,
                raw_material_location_id=source_lot.raw_material_location_id,
                raw_material_inventory_lot_id=source_lot.raw_material_inventory_lot_id,
                lot_no=source_lot.lot_no,
                movement_type="TRANSFER_OUT",
                qty=-qty,
                balance_after=source_inventory.current_qty,
                unit_cost_snapshot=source_lot.unit_cost,
                amount_snapshot=_money(qty, source_lot.unit_cost),
                source_type="SELF_USE_SHEET_JOB",
                source_id=job.self_use_sheet_job_id,
                transfer_key=transfer_key,
                memo=memo,
            ),
            RawMaterialInventoryMovement(
                raw_material_id=target_lot.raw_material_id,
                raw_material_location_id=target_lot.raw_material_location_id,
                raw_material_inventory_lot_id=target_lot.raw_material_inventory_lot_id,
                lot_no=target_lot.lot_no,
                movement_type="TRANSFER_IN",
                qty=qty,
                balance_after=target_inventory.current_qty,
                unit_cost_snapshot=target_lot.unit_cost,
                amount_snapshot=_money(qty, target_lot.unit_cost),
                source_type="SELF_USE_SHEET_JOB",
                source_id=job.self_use_sheet_job_id,
                transfer_key=transfer_key,
                memo=memo,
            ),
        ]
    )
    db.flush()
    return target_lot, transfer_key


def _consume_raw_material(
    db: Session,
    *,
    inventory_lot: RawMaterialInventoryLot,
    qty: Decimal,
    job: SelfUseSheetJob,
    memo: str,
) -> RawMaterialInventoryMovement:
    qty = _q2(qty)
    inventory = _get_inventory(
        db,
        raw_material_id=inventory_lot.raw_material_id,
        location_id=inventory_lot.raw_material_location_id,
    )
    if inventory_lot.current_qty < qty or inventory.current_qty < qty:
        raise HTTPException(status_code=409, detail=f"Raw material LOT {inventory_lot.lot_no} inventory is insufficient")
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
        amount_snapshot=_money(qty, inventory_lot.unit_cost),
        source_type="SELF_USE_SHEET_JOB",
        source_id=job.self_use_sheet_job_id,
        memo=memo,
    )
    db.add(movement)
    db.flush()
    return movement


def _reverse_raw_material(
    db: Session,
    *,
    original_lot: RawMaterialInventoryLot,
    qty: Decimal,
    unit_cost: Decimal | None,
    job: SelfUseSheetJob,
    memo: str,
) -> RawMaterialInventoryMovement:
    qty = _q2(qty)
    inventory = _get_inventory(
        db,
        raw_material_id=original_lot.raw_material_id,
        location_id=original_lot.raw_material_location_id,
    )
    original_lot.current_qty = _q2(original_lot.current_qty + qty)
    inventory.current_qty = _q2(inventory.current_qty + qty)
    movement = RawMaterialInventoryMovement(
        raw_material_id=original_lot.raw_material_id,
        raw_material_location_id=original_lot.raw_material_location_id,
        raw_material_inventory_lot_id=original_lot.raw_material_inventory_lot_id,
        lot_no=original_lot.lot_no,
        movement_type="CONSUME_REVERSE",
        qty=qty,
        balance_after=inventory.current_qty,
        unit_cost_snapshot=unit_cost,
        amount_snapshot=_money(qty, unit_cost),
        source_type="SELF_USE_SHEET_JOB",
        source_id=job.self_use_sheet_job_id,
        memo=memo,
    )
    db.add(movement)
    db.flush()
    return movement


def create_self_use_sheet_job(
    db: Session,
    payload: SelfUseSheetJobCreate,
    *,
    actor: str,
) -> SelfUseSheetJobOut:
    partner = None
    if payload.execution_type == "OUTSOURCE":
        partner = db.get(Partner, payload.partner_id)
        if partner is None or not partner.is_active or partner.partner_type != "VENDOR":
            raise HTTPException(status_code=422, detail="Active vendor partner is required")

    lot_ids = [item.raw_material_inventory_lot_id for item in payload.allocations]
    if len(lot_ids) != len(set(lot_ids)):
        raise HTTPException(status_code=422, detail="The same raw material LOT cannot be allocated twice")
    lots = (
        db.execute(
            select(RawMaterialInventoryLot)
            .where(RawMaterialInventoryLot.raw_material_inventory_lot_id.in_(lot_ids))
            .order_by(RawMaterialInventoryLot.raw_material_inventory_lot_id.asc())
        )
        .scalars()
        .all()
    )
    if len(lots) != len(lot_ids):
        raise HTTPException(status_code=404, detail="Raw material inventory LOT not found")
    if len({lot.raw_material_id for lot in lots}) != 1:
        raise HTTPException(status_code=422, detail="One self-use sheet job can use only one raw material")
    materials = {
        material.raw_material_id: material
        for material in db.execute(
            select(RawMaterial).where(
                RawMaterial.raw_material_id.in_({lot.raw_material_id for lot in lots})
            )
        ).scalars()
    }
    if any(material.uom.strip().upper() != "M" for material in materials.values()):
        raise HTTPException(
            status_code=422,
            detail="Automatic self-use sheet calculation requires raw material UOM M",
        )

    total_planned_input = sum(
        (_q2(item.planned_qty) for item in payload.allocations),
        start=Decimal("0"),
    )
    calculated_output_qty = calculate_self_use_sheet_output_qty(
        input_length_m=total_planned_input,
        cut_width_mm=payload.cut_width_mm,
        cut_length_mm=payload.cut_length_mm,
    )
    if calculated_output_qty <= 0:
        raise HTTPException(
            status_code=422,
            detail="Cut dimensions must be whole millimeters and produce a positive expected sheet quantity",
        )
    if payload.planned_output_qty != calculated_output_qty:
        raise HTTPException(
            status_code=422,
            detail=f"Expected output quantity must be {calculated_output_qty}",
        )

    quantity_by_lot = {
        item.raw_material_inventory_lot_id: _q2(item.planned_qty)
        for item in payload.allocations
    }
    job = SelfUseSheetJob(
        use_no=_new_number("SUS"),
        purpose_type=payload.purpose_type,
        execution_type=payload.execution_type,
        partner_id=partner.partner_id if partner else None,
        status="DRAFT",
        cut_width_mm=_q2(payload.cut_width_mm),
        cut_length_mm=_q2(payload.cut_length_mm),
        planned_output_qty=payload.planned_output_qty,
        expected_processing_fee=_q2(payload.expected_processing_fee),
        memo=_normalize_text(payload.memo),
        created_by=actor,
        version=1,
    )
    db.add(job)
    db.flush()
    for lot in lots:
        job.allocations.append(
            SelfUseSheetRawMaterialAllocation(
                raw_material_id=lot.raw_material_id,
                source_location_id=lot.raw_material_location_id,
                original_inventory_lot_id=lot.raw_material_inventory_lot_id,
                lot_no=lot.lot_no,
                planned_qty=quantity_by_lot[lot.raw_material_inventory_lot_id],
                returned_qty=Decimal("0"),
                unit_cost_snapshot=lot.unit_cost,
                status="PLANNED",
            )
        )
    db.flush()
    return get_self_use_sheet_job(db, job.self_use_sheet_job_id)


def start_self_use_sheet_job(
    db: Session,
    job_id: int,
    payload: SelfUseSheetJobStart,
    *,
    actor: str,
) -> SelfUseSheetJobOut:
    job = _require_job(db, job_id, lock=True)
    _require_version(job.version, payload.expected_version)
    if job.status != "DRAFT":
        raise HTTPException(status_code=409, detail="Only draft jobs can be started")

    vendor_location = None
    if job.execution_type == "OUTSOURCE":
        vendor_location = _ensure_outsource_vendor_location(db, job.partner_id)

    allocations = (
        db.execute(
            select(SelfUseSheetRawMaterialAllocation)
            .where(SelfUseSheetRawMaterialAllocation.self_use_sheet_job_id == job_id)
            .order_by(SelfUseSheetRawMaterialAllocation.self_use_sheet_raw_material_allocation_id.asc())
            .with_for_update()
        )
        .scalars()
        .all()
    )
    for allocation in allocations:
        original_lot = (
            db.execute(
                select(RawMaterialInventoryLot)
                .where(
                    RawMaterialInventoryLot.raw_material_inventory_lot_id
                    == allocation.original_inventory_lot_id
                )
                .with_for_update()
            )
            .scalar_one_or_none()
        )
        if original_lot is None:
            raise HTTPException(status_code=409, detail=f"Original raw material LOT {allocation.lot_no} no longer exists")
        if original_lot.current_qty < allocation.planned_qty:
            raise HTTPException(status_code=409, detail=f"Raw material LOT {allocation.lot_no} inventory is insufficient")
        allocation.unit_cost_snapshot = original_lot.unit_cost
        if job.execution_type == "INTERNAL":
            movement = _consume_raw_material(
                db,
                inventory_lot=original_lot,
                qty=allocation.planned_qty,
                job=job,
                memo=f"{job.use_no} 자가사용 시트지 내부 재단 투입",
            )
            allocation.issue_movement_id = movement.raw_material_inventory_movement_id
            allocation.processing_inventory_lot_id = original_lot.raw_material_inventory_lot_id
        else:
            processing_lot, transfer_key = _transfer_raw_material(
                db,
                source_lot=original_lot,
                to_location_id=vendor_location.raw_material_location_id,
                qty=allocation.planned_qty,
                job=job,
                memo=f"{job.use_no} 자가사용 시트지 외주 가공출고",
            )
            allocation.processing_inventory_lot_id = processing_lot.raw_material_inventory_lot_id
            allocation.dispatch_transfer_key = transfer_key or None
        allocation.status = "ISSUED"

    job.status = "IN_PROGRESS"
    job.started_by = actor
    job.started_at = utc_now()
    job.version += 1
    db.flush()
    return get_self_use_sheet_job(db, job_id)


def complete_self_use_sheet_job(
    db: Session,
    job_id: int,
    payload: SelfUseSheetJobComplete,
    *,
    actor: str,
) -> SelfUseSheetJobOut:
    job = _require_job(db, job_id, lock=True)
    _require_version(job.version, payload.expected_version)
    if job.status != "IN_PROGRESS":
        raise HTTPException(status_code=409, detail="Only in-progress jobs can be completed")

    allocations = (
        db.execute(
            select(SelfUseSheetRawMaterialAllocation)
            .where(SelfUseSheetRawMaterialAllocation.self_use_sheet_job_id == job_id)
            .order_by(SelfUseSheetRawMaterialAllocation.self_use_sheet_raw_material_allocation_id.asc())
            .with_for_update()
        )
        .scalars()
        .all()
    )
    result_by_id = {item.allocation_id: item for item in payload.allocations}
    if set(result_by_id) != {item.self_use_sheet_raw_material_allocation_id for item in allocations}:
        raise HTTPException(status_code=422, detail="Completion allocations must match the job allocations")

    total_actual = Decimal("0")
    material_amount = Decimal("0")
    for allocation in allocations:
        result = result_by_id[allocation.self_use_sheet_raw_material_allocation_id]
        actual_qty = _q2(result.actual_consumed_qty)
        returned_qty = _q2(result.returned_qty)
        if actual_qty + returned_qty != _q2(allocation.planned_qty):
            raise HTTPException(
                status_code=422,
                detail=f"Actual and returned quantities must equal planned quantity for LOT {allocation.lot_no}",
            )
        original_lot = (
            db.execute(
                select(RawMaterialInventoryLot)
                .where(RawMaterialInventoryLot.raw_material_inventory_lot_id == allocation.original_inventory_lot_id)
                .with_for_update()
            )
            .scalar_one_or_none()
        )
        if original_lot is None:
            raise HTTPException(status_code=409, detail=f"Original raw material LOT {allocation.lot_no} no longer exists")

        if job.execution_type == "OUTSOURCE":
            processing_lot = (
                db.execute(
                    select(RawMaterialInventoryLot)
                    .where(
                        RawMaterialInventoryLot.raw_material_inventory_lot_id
                        == allocation.processing_inventory_lot_id
                    )
                    .with_for_update()
                )
                .scalar_one_or_none()
            )
            if processing_lot is None:
                raise HTTPException(status_code=409, detail=f"Processing raw material LOT {allocation.lot_no} no longer exists")
            movement = _consume_raw_material(
                db,
                inventory_lot=processing_lot,
                qty=actual_qty,
                job=job,
                memo=f"{job.use_no} 자가사용 시트지 재단완료 투입",
            )
            allocation.issue_movement_id = movement.raw_material_inventory_movement_id
            if returned_qty > 0:
                _, return_key = _transfer_raw_material(
                    db,
                    source_lot=processing_lot,
                    to_location_id=allocation.source_location_id,
                    qty=returned_qty,
                    job=job,
                    memo=f"{job.use_no} 자가사용 시트지 미사용 원자재 반환",
                )
                allocation.return_transfer_key = return_key or None
        elif returned_qty > 0:
            _reverse_raw_material(
                db,
                original_lot=original_lot,
                qty=returned_qty,
                unit_cost=allocation.unit_cost_snapshot,
                job=job,
                memo=f"{job.use_no} 자가사용 시트지 내부 재단 미사용 원자재 반환",
            )

        allocation.actual_consumed_qty = actual_qty
        allocation.returned_qty = returned_qty
        allocation.amount_snapshot = _money(actual_qty, allocation.unit_cost_snapshot)
        allocation.status = "CONSUMED"
        total_actual += actual_qty
        material_amount += allocation.amount_snapshot

    now = utc_now()
    processing_fee = _q2(payload.actual_processing_fee)
    total_cost = _q2(material_amount + processing_fee)
    unit_cost = (total_cost / Decimal(payload.produced_qty)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    raw_material_id = allocations[0].raw_material_id
    sheet_lot = SelfUseSheetInventoryLot(
        self_use_sheet_job_id=job.self_use_sheet_job_id,
        raw_material_id=raw_material_id,
        sheet_lot_no=_new_number("SHEET"),
        source_lot_summary=", ".join(sorted({item.lot_no for item in allocations})),
        cut_width_mm=job.cut_width_mm,
        cut_length_mm=job.cut_length_mm,
        initial_qty=payload.produced_qty,
        current_qty=payload.produced_qty,
        material_amount=_q2(material_amount),
        processing_fee=processing_fee,
        total_cost=total_cost,
        unit_cost=unit_cost,
        status="AVAILABLE",
        version=1,
        completed_at=now,
    )
    db.add(sheet_lot)
    db.flush()
    job.sheet_lot = sheet_lot
    initial_location_id = allocations[0].source_location_id
    initial_balance = SelfUseSheetInventoryBalance(
        self_use_sheet_inventory_lot_id=sheet_lot.self_use_sheet_inventory_lot_id,
        raw_material_location_id=initial_location_id,
        current_qty=payload.produced_qty,
    )
    db.add(initial_balance)
    db.flush()
    db.add(
        SelfUseSheetInventoryMovement(
            self_use_sheet_inventory_lot_id=sheet_lot.self_use_sheet_inventory_lot_id,
            movement_type="PRODUCE_IN",
            raw_material_location_id=initial_location_id,
            qty=payload.produced_qty,
            balance_after=payload.produced_qty,
            location_balance_after=payload.produced_qty,
            purpose_type=job.purpose_type,
            unit_cost_snapshot=unit_cost,
            amount_snapshot=total_cost,
            memo=_normalize_text(payload.memo) or f"{job.use_no} 재단 완료",
            created_by=actor,
        )
    )

    job.status = "COMPLETED"
    job.actual_processing_fee = processing_fee
    job.actual_input_qty = _q2(total_actual)
    job.produced_qty = payload.produced_qty
    job.scrap_qty = payload.scrap_qty
    if _normalize_text(payload.memo):
        job.memo = _normalize_text(payload.memo)
    job.completed_by = actor
    job.completed_at = now
    job.version += 1
    db.flush()
    return get_self_use_sheet_job(db, job_id)


def cancel_self_use_sheet_job(
    db: Session,
    job_id: int,
    payload: SelfUseSheetJobCancel,
    *,
    actor: str,
) -> SelfUseSheetJobOut:
    job = _require_job(db, job_id, lock=True)
    _require_version(job.version, payload.expected_version)
    if job.status == "CANCELED":
        raise HTTPException(status_code=409, detail="The job is already canceled")

    allocations = (
        db.execute(
            select(SelfUseSheetRawMaterialAllocation)
            .where(SelfUseSheetRawMaterialAllocation.self_use_sheet_job_id == job_id)
            .order_by(SelfUseSheetRawMaterialAllocation.self_use_sheet_raw_material_allocation_id.asc())
            .with_for_update()
        )
        .scalars()
        .all()
    )
    reason = payload.reason.strip()
    if job.status == "DRAFT":
        for allocation in allocations:
            allocation.status = "REVERSED"
    elif job.status == "IN_PROGRESS":
        for allocation in allocations:
            original_lot = (
                db.execute(
                    select(RawMaterialInventoryLot)
                    .where(RawMaterialInventoryLot.raw_material_inventory_lot_id == allocation.original_inventory_lot_id)
                    .with_for_update()
                )
                .scalar_one_or_none()
            )
            if original_lot is None:
                raise HTTPException(status_code=409, detail=f"Original raw material LOT {allocation.lot_no} no longer exists")
            if job.execution_type == "INTERNAL":
                _reverse_raw_material(
                    db,
                    original_lot=original_lot,
                    qty=allocation.planned_qty,
                    unit_cost=allocation.unit_cost_snapshot,
                    job=job,
                    memo=f"{job.use_no} 취소: {reason}",
                )
            else:
                processing_lot = (
                    db.execute(
                        select(RawMaterialInventoryLot)
                        .where(
                            RawMaterialInventoryLot.raw_material_inventory_lot_id
                            == allocation.processing_inventory_lot_id
                        )
                        .with_for_update()
                    )
                    .scalar_one_or_none()
                )
                if processing_lot is None:
                    raise HTTPException(status_code=409, detail=f"Processing raw material LOT {allocation.lot_no} no longer exists")
                _transfer_raw_material(
                    db,
                    source_lot=processing_lot,
                    to_location_id=allocation.source_location_id,
                    qty=allocation.planned_qty,
                    job=job,
                    memo=f"{job.use_no} 가공출고 취소: {reason}",
                )
            allocation.status = "REVERSED"
    elif job.status == "COMPLETED":
        sheet_lot = (
            db.execute(
                select(SelfUseSheetInventoryLot)
                .where(SelfUseSheetInventoryLot.self_use_sheet_job_id == job_id)
                .with_for_update()
            )
            .scalar_one_or_none()
        )
        if sheet_lot is None or sheet_lot.status == "CANCELED":
            raise HTTPException(status_code=409, detail="Completed self-use sheet inventory was not found")
        if sheet_lot.current_qty != sheet_lot.initial_qty:
            raise HTTPException(status_code=409, detail="A completed job cannot be canceled after sheet inventory was used")
        balances = (
            db.execute(
                select(SelfUseSheetInventoryBalance)
                .where(
                    SelfUseSheetInventoryBalance.self_use_sheet_inventory_lot_id
                    == sheet_lot.self_use_sheet_inventory_lot_id,
                    SelfUseSheetInventoryBalance.current_qty > 0,
                )
                .order_by(SelfUseSheetInventoryBalance.self_use_sheet_inventory_balance_id.asc())
                .with_for_update()
            )
            .scalars()
            .all()
        )
        remaining_total = sheet_lot.current_qty
        for balance in balances:
            cancel_qty = balance.current_qty
            remaining_total -= cancel_qty
            balance.current_qty = 0
            db.add(
                SelfUseSheetInventoryMovement(
                    self_use_sheet_inventory_lot_id=sheet_lot.self_use_sheet_inventory_lot_id,
                    movement_type="CANCEL_OUT",
                    raw_material_location_id=balance.raw_material_location_id,
                    qty=-cancel_qty,
                    balance_after=remaining_total,
                    location_balance_after=0,
                    purpose_type=job.purpose_type,
                    unit_cost_snapshot=sheet_lot.unit_cost,
                    amount_snapshot=_money(cancel_qty, sheet_lot.unit_cost),
                    memo=reason,
                    created_by=actor,
                )
            )
        sheet_lot.current_qty = 0
        sheet_lot.status = "CANCELED"
        sheet_lot.version += 1
        for allocation in allocations:
            original_lot = (
                db.execute(
                    select(RawMaterialInventoryLot)
                    .where(RawMaterialInventoryLot.raw_material_inventory_lot_id == allocation.original_inventory_lot_id)
                    .with_for_update()
                )
                .scalar_one_or_none()
            )
            if original_lot is None:
                raise HTTPException(status_code=409, detail=f"Original raw material LOT {allocation.lot_no} no longer exists")
            _reverse_raw_material(
                db,
                original_lot=original_lot,
                qty=allocation.actual_consumed_qty or Decimal("0"),
                unit_cost=allocation.unit_cost_snapshot,
                job=job,
                memo=f"{job.use_no} 완료 취소: {reason}",
            )
            allocation.status = "REVERSED"

    job.status = "CANCELED"
    job.cancel_reason = reason
    job.canceled_by = actor
    job.canceled_at = utc_now()
    job.version += 1
    db.flush()
    return get_self_use_sheet_job(db, job_id)


def use_self_use_sheet_inventory(
    db: Session,
    lot_id: int,
    payload: SelfUseSheetUseIn,
    *,
    actor: str,
) -> SelfUseSheetInventoryLotOut:
    lot = (
        db.execute(
            select(SelfUseSheetInventoryLot)
            .where(SelfUseSheetInventoryLot.self_use_sheet_inventory_lot_id == lot_id)
            .with_for_update()
        )
        .scalar_one_or_none()
    )
    if lot is None:
        raise HTTPException(status_code=404, detail="Self-use sheet inventory LOT not found")
    _require_version(lot.version, payload.expected_version)
    if lot.status not in {"AVAILABLE", "DEPLETED"} or lot.current_qty < payload.qty:
        raise HTTPException(status_code=409, detail="Self-use sheet inventory is insufficient")
    if lot.current_qty <= 0:
        raise HTTPException(status_code=409, detail="Self-use sheet inventory is depleted")

    location_balance = _resolve_usage_balance(
        db,
        lot_id=lot.self_use_sheet_inventory_lot_id,
        location_id=payload.raw_material_location_id,
    )
    if location_balance.current_qty < payload.qty:
        raise HTTPException(status_code=409, detail="Self-use sheet inventory is insufficient at the selected location")

    lot.current_qty -= payload.qty
    location_balance.current_qty -= payload.qty
    lot.status = "DEPLETED" if lot.current_qty == 0 else "AVAILABLE"
    lot.version += 1
    db.add(
        SelfUseSheetInventoryMovement(
            self_use_sheet_inventory_lot_id=lot.self_use_sheet_inventory_lot_id,
            movement_type="USE_OUT",
            raw_material_location_id=location_balance.raw_material_location_id,
            qty=-payload.qty,
            balance_after=lot.current_qty,
            location_balance_after=location_balance.current_qty,
            purpose_type=payload.purpose_type,
            unit_cost_snapshot=lot.unit_cost,
            amount_snapshot=_money(payload.qty, lot.unit_cost),
            memo=_normalize_text(payload.memo),
            created_by=actor,
        )
    )
    db.flush()
    return get_self_use_sheet_inventory_lot(db, lot_id)


def reverse_self_use_sheet_usage(
    db: Session,
    movement_id: int,
    payload: SelfUseSheetUseReverseIn,
    *,
    actor: str,
) -> SelfUseSheetInventoryLotOut:
    movement = (
        db.execute(
            select(SelfUseSheetInventoryMovement)
            .where(SelfUseSheetInventoryMovement.self_use_sheet_inventory_movement_id == movement_id)
            .with_for_update()
        )
        .scalar_one_or_none()
    )
    if movement is None or movement.movement_type != "USE_OUT":
        raise HTTPException(status_code=404, detail="Self-use sheet usage movement not found")
    already_reversed = db.scalar(
        select(func.count())
        .select_from(SelfUseSheetInventoryMovement)
        .where(SelfUseSheetInventoryMovement.source_movement_id == movement_id)
    )
    if already_reversed:
        raise HTTPException(status_code=409, detail="The usage movement is already reversed")
    lot = (
        db.execute(
            select(SelfUseSheetInventoryLot)
            .where(
                SelfUseSheetInventoryLot.self_use_sheet_inventory_lot_id
                == movement.self_use_sheet_inventory_lot_id
            )
            .with_for_update()
        )
        .scalar_one()
    )
    _require_version(lot.version, payload.expected_version)
    if lot.status == "CANCELED":
        raise HTTPException(status_code=409, detail="Canceled inventory cannot be restored")
    restore_qty = abs(movement.qty)
    location_balance = _get_sheet_balance(
        db,
        lot_id=lot.self_use_sheet_inventory_lot_id,
        location_id=movement.raw_material_location_id,
        lock=True,
        create=True,
    )
    lot.current_qty += restore_qty
    location_balance.current_qty += restore_qty
    lot.status = "AVAILABLE"
    lot.version += 1
    db.add(
        SelfUseSheetInventoryMovement(
            self_use_sheet_inventory_lot_id=lot.self_use_sheet_inventory_lot_id,
            movement_type="USE_REVERSE",
            raw_material_location_id=movement.raw_material_location_id,
            qty=restore_qty,
            balance_after=lot.current_qty,
            location_balance_after=location_balance.current_qty,
            purpose_type=movement.purpose_type,
            unit_cost_snapshot=movement.unit_cost_snapshot,
            amount_snapshot=movement.amount_snapshot,
            source_movement_id=movement.self_use_sheet_inventory_movement_id,
            memo=payload.reason.strip(),
            created_by=actor,
        )
    )
    db.flush()
    return get_self_use_sheet_inventory_lot(db, lot.self_use_sheet_inventory_lot_id)


def transfer_self_use_sheet_inventory(
    db: Session,
    lot_id: int,
    payload: SelfUseSheetTransferIn,
    *,
    actor: str,
) -> SelfUseSheetInventoryLotOut:
    lot = (
        db.execute(
            select(SelfUseSheetInventoryLot)
            .where(SelfUseSheetInventoryLot.self_use_sheet_inventory_lot_id == lot_id)
            .with_for_update()
        )
        .scalar_one_or_none()
    )
    if lot is None:
        raise HTTPException(status_code=404, detail="Self-use sheet inventory LOT not found")
    _require_version(lot.version, payload.expected_version)
    if lot.status != "AVAILABLE":
        raise HTTPException(status_code=409, detail="Only available self-use sheet inventory can be transferred")

    target_location = db.get(RawMaterialLocation, payload.to_location_id)
    if target_location is None or not target_location.is_active:
        raise HTTPException(status_code=422, detail="Active target location is required")
    source_balance = _get_sheet_balance(
        db,
        lot_id=lot_id,
        location_id=payload.from_location_id,
        lock=True,
    )
    if source_balance is None or source_balance.current_qty < payload.qty:
        raise HTTPException(status_code=409, detail="Self-use sheet inventory is insufficient at the source location")
    target_balance = _get_sheet_balance(
        db,
        lot_id=lot_id,
        location_id=payload.to_location_id,
        lock=True,
        create=True,
    )

    transfer_key = f"SHEET-TRANSFER-{uuid4().hex.upper()}"
    source_balance.current_qty -= payload.qty
    target_balance.current_qty += payload.qty
    lot.version += 1
    amount = _money(payload.qty, lot.unit_cost)
    for movement_type, location_id, counterpart_id, qty, location_after in (
        (
            "TRANSFER_OUT",
            payload.from_location_id,
            payload.to_location_id,
            -payload.qty,
            source_balance.current_qty,
        ),
        (
            "TRANSFER_IN",
            payload.to_location_id,
            payload.from_location_id,
            payload.qty,
            target_balance.current_qty,
        ),
    ):
        db.add(
            SelfUseSheetInventoryMovement(
                self_use_sheet_inventory_lot_id=lot_id,
                movement_type=movement_type,
                raw_material_location_id=location_id,
                counterpart_location_id=counterpart_id,
                qty=qty,
                balance_after=lot.current_qty,
                location_balance_after=location_after,
                unit_cost_snapshot=lot.unit_cost,
                amount_snapshot=amount,
                transfer_key=transfer_key,
                memo=payload.reason,
                created_by=actor,
            )
        )
    db.flush()
    return get_self_use_sheet_inventory_lot(db, lot_id)
