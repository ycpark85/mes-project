from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.time import korea_day_bounds_utc
from app.models.outsource_work_group_self_use_sheet_allocation import (
    OutsourceWorkGroupSelfUseSheetAllocation,
)
from app.models.partner import Partner
from app.models.raw_material import RawMaterial
from app.models.self_use_sheet_inventory_balance import SelfUseSheetInventoryBalance
from app.models.self_use_sheet_inventory_lot import SelfUseSheetInventoryLot
from app.models.self_use_sheet_inventory_movement import SelfUseSheetInventoryMovement
from app.models.self_use_sheet_job import SelfUseSheetJob
from app.models.self_use_sheet_raw_material_allocation import SelfUseSheetRawMaterialAllocation
from app.schemas.self_use_sheet import (
    SelfUseSheetAllocationOut,
    SelfUseSheetInventoryLocationOut,
    SelfUseSheetInventoryLotListOut,
    SelfUseSheetInventoryLotOut,
    SelfUseSheetInventorySummaryOut,
    SelfUseSheetJobListOut,
    SelfUseSheetJobOut,
    SelfUseSheetMovementListOut,
    SelfUseSheetMovementOut,
    SelfUseSheetSourceLotOut,
)
from app.services.inventory_usage_context import load_work_group_usage_contexts


def _q2(value: Decimal | int) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _job_statement():
    return select(SelfUseSheetJob).options(
        selectinload(SelfUseSheetJob.partner),
        selectinload(SelfUseSheetJob.sheet_lot),
        selectinload(SelfUseSheetJob.allocations).selectinload(
            SelfUseSheetRawMaterialAllocation.raw_material
        ),
        selectinload(SelfUseSheetJob.allocations).selectinload(
            SelfUseSheetRawMaterialAllocation.source_location
        ),
    )


def _job_out(job: SelfUseSheetJob) -> SelfUseSheetJobOut:
    return SelfUseSheetJobOut(
        self_use_sheet_job_id=job.self_use_sheet_job_id,
        use_no=job.use_no,
        purpose_type=job.purpose_type,
        execution_type=job.execution_type,
        partner_id=job.partner_id,
        partner_name=job.partner.name if job.partner else None,
        status=job.status,
        cut_width_mm=job.cut_width_mm,
        cut_length_mm=job.cut_length_mm,
        planned_output_qty=job.planned_output_qty,
        expected_processing_fee=job.expected_processing_fee,
        actual_processing_fee=job.actual_processing_fee,
        actual_input_qty=job.actual_input_qty,
        produced_qty=job.produced_qty,
        scrap_qty=job.scrap_qty,
        memo=job.memo,
        cancel_reason=job.cancel_reason,
        created_by=job.created_by,
        started_by=job.started_by,
        completed_by=job.completed_by,
        canceled_by=job.canceled_by,
        version=job.version,
        started_at=job.started_at,
        completed_at=job.completed_at,
        canceled_at=job.canceled_at,
        created_at=job.created_at,
        updated_at=job.updated_at,
        sheet_lot_id=job.sheet_lot.self_use_sheet_inventory_lot_id if job.sheet_lot else None,
        sheet_lot_no=job.sheet_lot.sheet_lot_no if job.sheet_lot else None,
        allocations=[
            SelfUseSheetAllocationOut(
                self_use_sheet_raw_material_allocation_id=item.self_use_sheet_raw_material_allocation_id,
                raw_material_id=item.raw_material_id,
                material_code=item.raw_material.material_code,
                material_name=item.raw_material.material_name,
                uom=item.raw_material.uom,
                source_location_id=item.source_location_id,
                source_location_name=item.source_location.location_name,
                original_inventory_lot_id=item.original_inventory_lot_id,
                processing_inventory_lot_id=item.processing_inventory_lot_id,
                lot_no=item.lot_no,
                planned_qty=item.planned_qty,
                actual_consumed_qty=item.actual_consumed_qty,
                returned_qty=item.returned_qty,
                unit_cost_snapshot=item.unit_cost_snapshot,
                amount_snapshot=item.amount_snapshot,
                status=item.status,
            )
            for item in sorted(
                job.allocations,
                key=lambda row: row.self_use_sheet_raw_material_allocation_id,
            )
        ],
    )


def get_self_use_sheet_job(db: Session, job_id: int) -> SelfUseSheetJobOut:
    job = db.execute(
        _job_statement().where(SelfUseSheetJob.self_use_sheet_job_id == job_id)
    ).scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Self-use sheet job not found")
    return _job_out(job)


def list_self_use_sheet_jobs(
    db: Session,
    *,
    q: str | None,
    status: str | None,
    purpose_type: str | None,
    date_from: date | None,
    date_to: date | None,
    page: int,
    size: int,
) -> SelfUseSheetJobListOut:
    filters = []
    if status:
        filters.append(SelfUseSheetJob.status == status.strip().upper())
    if purpose_type:
        filters.append(SelfUseSheetJob.purpose_type == purpose_type.strip().upper())
    if date_from:
        filters.append(SelfUseSheetJob.created_at >= datetime.combine(date_from, time.min))
    if date_to:
        filters.append(SelfUseSheetJob.created_at < datetime.combine(date_to, time.max))
    query_text = (q or "").strip()
    if query_text:
        pattern = f"%{query_text}%"
        filters.append(
            or_(
                SelfUseSheetJob.use_no.ilike(pattern),
                SelfUseSheetJob.memo.ilike(pattern),
                SelfUseSheetJob.partner.has(Partner.name.ilike(pattern)),
                SelfUseSheetJob.allocations.any(
                    SelfUseSheetRawMaterialAllocation.lot_no.ilike(pattern)
                ),
            )
        )
    total = db.scalar(select(func.count()).select_from(SelfUseSheetJob).where(*filters)) or 0
    jobs = (
        db.execute(
            _job_statement()
            .where(*filters)
            .order_by(SelfUseSheetJob.created_at.desc(), SelfUseSheetJob.self_use_sheet_job_id.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        .scalars()
        .all()
    )
    return SelfUseSheetJobListOut(
        items=[_job_out(job) for job in jobs],
        total=int(total),
        page=page,
        size=size,
    )


def _inventory_filters(
    *,
    q: str | None,
    raw_material_id: int | None,
    status: str | None,
):
    filters = []
    if raw_material_id:
        filters.append(SelfUseSheetInventoryLot.raw_material_id == raw_material_id)
    if status:
        filters.append(SelfUseSheetInventoryLot.status == status.strip().upper())
    query_text = (q or "").strip()
    if query_text:
        pattern = f"%{query_text}%"
        filters.append(
            or_(
                SelfUseSheetInventoryLot.sheet_lot_no.ilike(pattern),
                SelfUseSheetInventoryLot.source_lot_summary.ilike(pattern),
                SelfUseSheetInventoryLot.raw_material.has(RawMaterial.material_code.ilike(pattern)),
                SelfUseSheetInventoryLot.raw_material.has(RawMaterial.material_name.ilike(pattern)),
            )
        )
    return filters


def _inventory_out(lot: SelfUseSheetInventoryLot) -> SelfUseSheetInventoryLotOut:
    job = lot.job
    return SelfUseSheetInventoryLotOut(
        self_use_sheet_inventory_lot_id=lot.self_use_sheet_inventory_lot_id,
        self_use_sheet_job_id=lot.self_use_sheet_job_id,
        use_no=job.use_no,
        purpose_type=job.purpose_type,
        execution_type=job.execution_type,
        partner_name=job.partner.name if job.partner else None,
        raw_material_id=lot.raw_material_id,
        material_code=lot.raw_material.material_code,
        material_name=lot.raw_material.material_name,
        sheet_lot_no=lot.sheet_lot_no,
        source_lot_summary=lot.source_lot_summary,
        cut_width_mm=lot.cut_width_mm,
        cut_length_mm=lot.cut_length_mm,
        initial_qty=lot.initial_qty,
        used_qty=lot.initial_qty - lot.current_qty,
        current_qty=lot.current_qty,
        material_amount=lot.material_amount,
        processing_fee=lot.processing_fee,
        total_cost=lot.total_cost,
        unit_cost=lot.unit_cost,
        status=lot.status,
        version=lot.version,
        completed_at=lot.completed_at,
        updated_at=lot.updated_at,
        locations=[
            SelfUseSheetInventoryLocationOut(
                raw_material_location_id=item.raw_material_location_id,
                location_code=item.location.location_code,
                location_name=item.location.location_name,
                location_type=item.location.location_type,
                current_qty=item.current_qty,
            )
            for item in sorted(
                lot.location_balances,
                key=lambda value: value.raw_material_location_id,
            )
            if item.current_qty > 0
        ],
        source_lots=[
            SelfUseSheetSourceLotOut(
                raw_material_inventory_lot_id=item.original_inventory_lot_id,
                raw_material_id=item.raw_material_id,
                material_code=item.raw_material.material_code,
                material_name=item.raw_material.material_name,
                source_location_id=item.source_location_id,
                source_location_name=item.source_location.location_name,
                lot_no=item.lot_no,
                actual_consumed_qty=item.actual_consumed_qty or Decimal("0"),
                unit_cost_snapshot=item.unit_cost_snapshot or Decimal("0"),
                amount_snapshot=item.amount_snapshot or Decimal("0"),
            )
            for item in job.allocations
        ],
    )


def _inventory_statement():
    return (
        select(SelfUseSheetInventoryLot)
        .execution_options(populate_existing=True)
        .options(
            selectinload(SelfUseSheetInventoryLot.raw_material),
            selectinload(SelfUseSheetInventoryLot.job).selectinload(SelfUseSheetJob.partner),
            selectinload(SelfUseSheetInventoryLot.location_balances).selectinload(
                SelfUseSheetInventoryBalance.location
            ),
            selectinload(SelfUseSheetInventoryLot.job)
            .selectinload(SelfUseSheetJob.allocations)
            .selectinload(SelfUseSheetRawMaterialAllocation.raw_material),
            selectinload(SelfUseSheetInventoryLot.job)
            .selectinload(SelfUseSheetJob.allocations)
            .selectinload(SelfUseSheetRawMaterialAllocation.source_location),
        )
    )


def list_self_use_sheet_inventory(
    db: Session,
    *,
    q: str | None,
    raw_material_id: int | None,
    status: str | None,
    page: int,
    size: int,
) -> SelfUseSheetInventoryLotListOut:
    filters = _inventory_filters(q=q, raw_material_id=raw_material_id, status=status)
    total = db.scalar(select(func.count()).select_from(SelfUseSheetInventoryLot).where(*filters)) or 0
    summary_filters = [*filters, SelfUseSheetInventoryLot.status != "CANCELED"]
    summary_row = db.execute(
        select(
            func.count(SelfUseSheetInventoryLot.self_use_sheet_inventory_lot_id),
            func.coalesce(func.sum(SelfUseSheetInventoryLot.initial_qty), 0),
            func.coalesce(
                func.sum(SelfUseSheetInventoryLot.initial_qty - SelfUseSheetInventoryLot.current_qty),
                0,
            ),
            func.coalesce(func.sum(SelfUseSheetInventoryLot.current_qty), 0),
            func.coalesce(
                func.sum(SelfUseSheetInventoryLot.current_qty * SelfUseSheetInventoryLot.unit_cost),
                0,
            ),
        ).where(*summary_filters)
    ).one()
    lots = (
        db.execute(
            _inventory_statement()
            .where(*filters)
            .order_by(
                SelfUseSheetInventoryLot.completed_at.desc(),
                SelfUseSheetInventoryLot.self_use_sheet_inventory_lot_id.desc(),
            )
            .offset((page - 1) * size)
            .limit(size)
        )
        .scalars()
        .all()
    )
    return SelfUseSheetInventoryLotListOut(
        items=[_inventory_out(lot) for lot in lots],
        total=int(total),
        page=page,
        size=size,
        summary=SelfUseSheetInventorySummaryOut(
            lot_count=int(summary_row[0] or 0),
            initial_qty=int(summary_row[1] or 0),
            used_qty=int(summary_row[2] or 0),
            current_qty=int(summary_row[3] or 0),
            inventory_amount=_q2(summary_row[4] or 0),
        ),
    )


def get_self_use_sheet_inventory_lot(db: Session, lot_id: int) -> SelfUseSheetInventoryLotOut:
    lot = db.execute(
        _inventory_statement().where(
            SelfUseSheetInventoryLot.self_use_sheet_inventory_lot_id == lot_id
        )
    ).scalar_one_or_none()
    if lot is None:
        raise HTTPException(status_code=404, detail="Self-use sheet inventory LOT not found")
    return _inventory_out(lot)


def list_self_use_sheet_movements(
    db: Session,
    lot_id: int | None = None,
    *,
    q: str | None = None,
    movement_type: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int,
    size: int,
) -> SelfUseSheetMovementListOut:
    if lot_id is not None and db.get(SelfUseSheetInventoryLot, lot_id) is None:
        raise HTTPException(status_code=404, detail="Self-use sheet inventory LOT not found")

    filters = []
    if lot_id is not None:
        filters.append(SelfUseSheetInventoryMovement.self_use_sheet_inventory_lot_id == lot_id)
    if q and q.strip():
        pattern = f"%{q.strip()}%"
        filters.append(
            SelfUseSheetInventoryMovement.inventory_lot.has(
                or_(
                    SelfUseSheetInventoryLot.sheet_lot_no.ilike(pattern),
                    SelfUseSheetInventoryLot.raw_material.has(
                        or_(
                            RawMaterial.material_code.ilike(pattern),
                            RawMaterial.material_name.ilike(pattern),
                        )
                    ),
                )
            )
        )
    if movement_type and movement_type.strip():
        filters.append(
            SelfUseSheetInventoryMovement.movement_type == movement_type.strip().upper()
        )
    if date_from is not None:
        from_dt, _ = korea_day_bounds_utc(date_from)
        filters.append(SelfUseSheetInventoryMovement.created_at >= from_dt)
    if date_to is not None:
        _, to_dt_exclusive = korea_day_bounds_utc(date_to)
        filters.append(SelfUseSheetInventoryMovement.created_at < to_dt_exclusive)

    total = db.scalar(
        select(func.count()).select_from(SelfUseSheetInventoryMovement).where(*filters)
    ) or 0
    rows = (
        db.execute(
            select(SelfUseSheetInventoryMovement)
            .options(
                selectinload(SelfUseSheetInventoryMovement.location),
                selectinload(SelfUseSheetInventoryMovement.counterpart_location),
                selectinload(SelfUseSheetInventoryMovement.inventory_lot).selectinload(
                    SelfUseSheetInventoryLot.raw_material
                ),
            )
            .where(*filters)
            .order_by(
                SelfUseSheetInventoryMovement.created_at.desc(),
                SelfUseSheetInventoryMovement.self_use_sheet_inventory_movement_id.desc(),
            )
            .offset((page - 1) * size)
            .limit(size)
        )
        .scalars()
        .all()
    )

    allocation_source_types = {
        "OUTSOURCE_WORK_GROUP_SELF_USE_SHEET_ALLOCATION",
        "OUTSOURCE_WORK_GROUP_CANCEL",
    }
    allocation_ids = {
        row.source_id
        for row in rows
        if row.source_id is not None and row.source_type in allocation_source_types
    }
    allocation_group_ids = (
        dict(
            db.execute(
                select(
                    OutsourceWorkGroupSelfUseSheetAllocation.outsource_work_group_self_use_sheet_allocation_id,
                    OutsourceWorkGroupSelfUseSheetAllocation.outsource_work_group_id,
                ).where(
                    OutsourceWorkGroupSelfUseSheetAllocation.outsource_work_group_self_use_sheet_allocation_id.in_(
                        allocation_ids
                    )
                )
            ).all()
        )
        if allocation_ids
        else {}
    )
    contexts = load_work_group_usage_contexts(db, set(allocation_group_ids.values()))

    items = []
    for row in rows:
        group_id = allocation_group_ids.get(row.source_id) if row.source_id is not None else None
        context = contexts.get(group_id) if group_id is not None else None
        items.append(
            SelfUseSheetMovementOut(
                self_use_sheet_inventory_movement_id=row.self_use_sheet_inventory_movement_id,
                self_use_sheet_inventory_lot_id=row.self_use_sheet_inventory_lot_id,
                inventory_lot_version=row.inventory_lot.version,
                sheet_lot_no=row.inventory_lot.sheet_lot_no,
                material_name=row.inventory_lot.raw_material.material_name,
                movement_type=row.movement_type,
                raw_material_location_id=row.raw_material_location_id,
                location_name=row.location.location_name,
                counterpart_location_id=row.counterpart_location_id,
                counterpart_location_name=(
                    row.counterpart_location.location_name if row.counterpart_location else None
                ),
                qty=row.qty,
                balance_after=row.balance_after,
                location_balance_after=row.location_balance_after,
                purpose_type=row.purpose_type,
                unit_cost_snapshot=row.unit_cost_snapshot,
                amount_snapshot=row.amount_snapshot,
                source_movement_id=row.source_movement_id,
                source_type=row.source_type,
                source_id=row.source_id,
                transfer_key=row.transfer_key,
                memo=row.memo,
                usage_product_display=context.product_display if context else "-",
                usage_lot_display=context.lot_display if context else "-",
                usage_partner_display=context.partner_display if context else "-",
                work_instruction_no=context.work_instruction_no if context else "-",
                work_group_seq=context.work_group_seq if context else "-",
                created_by=row.created_by,
                created_at=row.created_at,
            )
        )

    return SelfUseSheetMovementListOut(
        items=items,
        total=int(total),
        page=page,
        size=size,
    )
