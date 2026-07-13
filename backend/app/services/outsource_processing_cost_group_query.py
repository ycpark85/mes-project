from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.models.outsource_processing_cost_allocation import (
    OutsourceProcessingCostAllocation,
)
from app.models.outsource_processing_cost_group import OutsourceProcessingCostGroup
from app.models.outsource_processing_cost_work_group import (
    OutsourceProcessingCostWorkGroup,
)
from app.models.outsource_work_group import OutsourceWorkGroup
from app.models.outsource_work_instruction import OutsourceWorkInstruction
from app.models.partner import Partner
from app.schemas.outsource_processing_cost import (
    OutsourceProcessingCostAllocationOut,
    OutsourceProcessingCostGroupListItemOut,
    OutsourceProcessingCostGroupListOut,
)
from app.services.outsource_processing_cost_common import (
    normalize_month,
    normalize_process_type,
    normalize_status,
)


def list_outsource_processing_cost_groups(
    db: Session,
    *,
    settlement_month: date | None = None,
    process_type: str | None = None,
    status: str | None = None,
    q: str | None = None,
) -> OutsourceProcessingCostGroupListOut:
    normalized_process_type = normalize_process_type(process_type) if process_type else None
    normalized_status = normalize_status(status) if status else None
    normalized_month = normalize_month(settlement_month) if settlement_month else None

    stmt = select(OutsourceProcessingCostGroup).order_by(
        OutsourceProcessingCostGroup.settlement_month.desc(),
        OutsourceProcessingCostGroup.created_at.desc(),
        OutsourceProcessingCostGroup.outsource_processing_cost_group_id.desc(),
    )

    if normalized_month:
        stmt = stmt.where(OutsourceProcessingCostGroup.settlement_month == normalized_month)

    if normalized_process_type:
        stmt = stmt.where(OutsourceProcessingCostGroup.process_type == normalized_process_type)

    if normalized_status == "COST_VARIANCE":
        stmt = stmt.where(
            OutsourceProcessingCostGroup.status == "DRAFT",
            OutsourceProcessingCostGroup.standard_amount.is_not(None),
            OutsourceProcessingCostGroup.actual_amount.is_not(None),
            OutsourceProcessingCostGroup.actual_amount
            != OutsourceProcessingCostGroup.standard_amount,
        )
    elif normalized_status:
        stmt = stmt.where(OutsourceProcessingCostGroup.status == normalized_status)
    else:
        stmt = stmt.where(OutsourceProcessingCostGroup.status != "CANCELED")

    if q and q.strip():
        like = f"%{q.strip()}%"
        allocation_exists = (
            select(OutsourceProcessingCostAllocation.outsource_processing_cost_allocation_id)
            .where(
                OutsourceProcessingCostAllocation.outsource_processing_cost_group_id
                == OutsourceProcessingCostGroup.outsource_processing_cost_group_id
            )
            .where(
                (OutsourceProcessingCostAllocation.lot_no_snapshot.like(like))
                | (OutsourceProcessingCostAllocation.product_code_snapshot.like(like))
                | (OutsourceProcessingCostAllocation.product_name_snapshot.like(like))
            )
            .limit(1)
        )
        stmt = stmt.where(
            (OutsourceProcessingCostGroup.cost_group_no.like(like))
            | exists(allocation_exists)
        )

    groups = db.execute(stmt).scalars().all()
    items = [build_processing_cost_group_out(db, group) for group in groups]

    standard_total = sum((item.standard_amount or Decimal("0")) for item in items)
    actual_total = sum((item.actual_amount or Decimal("0")) for item in items)

    return OutsourceProcessingCostGroupListOut(
        items=items,
        total_count=len(items),
        standard_total=standard_total,
        actual_total=actual_total,
        difference_total=actual_total - standard_total,
        unclosed_count=sum(1 for item in items if item.status == "DRAFT"),
    )


def build_processing_cost_group_out(
    db: Session,
    group: OutsourceProcessingCostGroup,
) -> OutsourceProcessingCostGroupListItemOut:
    allocations = (
        db.execute(
            select(OutsourceProcessingCostAllocation)
            .where(
                OutsourceProcessingCostAllocation.outsource_processing_cost_group_id
                == group.outsource_processing_cost_group_id
            )
            .order_by(
                OutsourceProcessingCostAllocation.lot_no_snapshot.asc(),
                OutsourceProcessingCostAllocation.outsource_processing_cost_allocation_id.asc(),
            )
        )
        .scalars()
        .all()
    )

    work_group_rows = (
        db.execute(
            select(
                OutsourceProcessingCostWorkGroup,
                OutsourceWorkGroup,
                OutsourceWorkInstruction,
                Partner,
            )
            .join(
                OutsourceWorkGroup,
                OutsourceWorkGroup.outsource_work_group_id
                == OutsourceProcessingCostWorkGroup.outsource_work_group_id,
            )
            .join(
                OutsourceWorkInstruction,
                OutsourceWorkInstruction.outsource_work_instruction_id
                == OutsourceWorkGroup.outsource_work_instruction_id,
            )
            .join(Partner, Partner.partner_id == OutsourceWorkInstruction.partner_id)
            .where(
                OutsourceProcessingCostWorkGroup.outsource_processing_cost_group_id
                == group.outsource_processing_cost_group_id
            )
        )
        .all()
    )

    allocation_items = [
        build_processing_cost_allocation_out(allocation)
        for allocation in allocations
    ]
    standard_amount = group.standard_amount
    actual_amount = group.actual_amount
    difference = (
        actual_amount - standard_amount
        if actual_amount is not None and standard_amount is not None
        else None
    )

    return OutsourceProcessingCostGroupListItemOut(
        outsource_processing_cost_group_id=group.outsource_processing_cost_group_id,
        cost_group_no=group.cost_group_no,
        settlement_month=group.settlement_month,
        process_type=group.process_type,
        status=group.status,
        work_group_count=len(work_group_rows),
        lot_count=len({allocation.lot_id for allocation in allocations}),
        partner_names=list(dict.fromkeys(row[3].name for row in work_group_rows if row[3].name)),
        instruction_nos=list(dict.fromkeys(row[2].instruction_no for row in work_group_rows)),
        lot_nos=list(dict.fromkeys(allocation.lot_no_snapshot for allocation in allocations)),
        product_names=list(
            dict.fromkeys(
                allocation.product_name_snapshot
                for allocation in allocations
                if allocation.product_name_snapshot
            )
        ),
        standard_amount=standard_amount,
        actual_amount=actual_amount,
        amount_difference=difference,
        standard_memo=group.standard_memo,
        actual_billing_month=group.actual_billing_month,
        actual_memo=group.actual_memo,
        remark=group.remark,
        closed_at=group.closed_at,
        canceled_at=group.canceled_at,
        created_at=group.created_at,
        updated_at=group.updated_at,
        allocations=allocation_items,
    )


def build_processing_cost_allocation_out(
    allocation: OutsourceProcessingCostAllocation,
) -> OutsourceProcessingCostAllocationOut:
    standard_amount = allocation.standard_allocated_amount
    actual_amount = allocation.actual_allocated_amount
    difference = (
        actual_amount - standard_amount
        if actual_amount is not None and standard_amount is not None
        else None
    )

    return OutsourceProcessingCostAllocationOut(
        outsource_processing_cost_allocation_id=allocation.outsource_processing_cost_allocation_id,
        lot_id=allocation.lot_id,
        lot_no=allocation.lot_no_snapshot,
        product_code=allocation.product_code_snapshot,
        product_name=allocation.product_name_snapshot,
        product_spec=allocation.product_spec_snapshot,
        panel_width_mm=allocation.panel_width_mm_snapshot,
        panel_length_mm=allocation.panel_length_mm_snapshot,
        cuts_per_sheet=allocation.cuts_per_sheet_snapshot,
        sheet_qty=allocation.sheet_qty_snapshot,
        instruction_output_qty=allocation.instruction_output_qty_snapshot,
        basis_type=allocation.basis_type,
        basis_value=allocation.basis_value,
        basis_area_sqm=allocation.basis_area_sqm,
        allocation_ratio=allocation.allocation_ratio,
        standard_allocated_amount=standard_amount,
        actual_allocated_amount=actual_amount,
        amount_difference=difference,
    )
