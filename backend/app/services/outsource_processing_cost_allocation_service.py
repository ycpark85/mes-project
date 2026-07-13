from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.lot import Lot
from app.models.outsource_processing_cost_allocation import (
    OutsourceProcessingCostAllocation,
)
from app.models.outsource_processing_cost_group import OutsourceProcessingCostGroup
from app.models.outsource_work_group import OutsourceWorkGroup
from app.models.outsource_work_group_item import OutsourceWorkGroupItem
from app.models.product import Product
from app.services.outsource_processing_cost_basis import (
    calculate_area_basis,
    get_work_group_item_rows,
    resolve_instruction_output_qty,
)


MONEY_QUANT = Decimal("1")


@dataclass
class AllocationSource:
    lot: Lot
    product: Product
    work_group: OutsourceWorkGroup | None
    work_group_item: OutsourceWorkGroupItem | None
    cuts_per_sheet: int | None
    sheet_qty: int | None
    instruction_output_qty: int | None
    basis_type: str
    basis_value: Decimal
    basis_area_sqm: Decimal | None


def build_allocation_sources(
    db: Session,
    process_type: str,
    work_group_ids: list[int],
    lot_ids: list[int],
) -> list[AllocationSource]:
    sources: list[AllocationSource] = []

    if work_group_ids:
        work_groups = (
            db.execute(
                select(OutsourceWorkGroup)
                .where(OutsourceWorkGroup.outsource_work_group_id.in_(work_group_ids))
                .order_by(OutsourceWorkGroup.outsource_work_group_id.asc())
            )
            .scalars()
            .all()
        )

        if len(work_groups) != len(work_group_ids):
            raise HTTPException(status_code=404, detail="선택한 외주작업 묶음을 찾을 수 없습니다.")

        for work_group in work_groups:
            if process_type == "PRINT" and work_group.process_type != process_type:
                raise HTTPException(status_code=409, detail="선택한 공정과 외주작업 묶음 공정이 다릅니다.")

            for group_item, lot, product in get_work_group_item_rows(
                db,
                work_group.outsource_work_group_id,
            ):
                output_qty = resolve_instruction_output_qty(work_group, group_item, lot)
                basis_type, basis_value, basis_area_sqm = _resolve_basis(
                    product,
                    output_qty,
                )
                sources.append(
                    AllocationSource(
                        lot=lot,
                        product=product,
                        work_group=work_group,
                        work_group_item=group_item,
                        cuts_per_sheet=group_item.cuts_per_sheet,
                        sheet_qty=work_group.sheet_qty,
                        instruction_output_qty=output_qty,
                        basis_type=basis_type,
                        basis_value=basis_value,
                        basis_area_sqm=basis_area_sqm,
                    )
                )

    if lot_ids:
        rows = (
            db.execute(
                select(Lot, Product)
                .join(Product, Product.product_id == Lot.product_id)
                .where(Lot.lot_id.in_(lot_ids))
                .order_by(Lot.lot_id.asc())
            )
            .all()
        )

        if len(rows) != len(lot_ids):
            raise HTTPException(status_code=404, detail="선택한 LOT를 찾을 수 없습니다.")

        for lot, product in rows:
            basis_type, basis_value, basis_area_sqm = _resolve_basis(
                product,
                lot.lot_qty,
            )
            sources.append(
                AllocationSource(
                    lot=lot,
                    product=product,
                    work_group=None,
                    work_group_item=None,
                    cuts_per_sheet=product.cut_qty_per_panel,
                    sheet_qty=None,
                    instruction_output_qty=lot.lot_qty,
                    basis_type=basis_type,
                    basis_value=basis_value,
                    basis_area_sqm=basis_area_sqm,
                )
            )

    validate_allocation_sources(sources)

    return sources


def replace_processing_cost_allocations(
    db: Session,
    cost_group: OutsourceProcessingCostGroup,
    sources: list[AllocationSource],
) -> None:
    for allocation in list(cost_group.allocations):
        db.delete(allocation)

    total_basis = sum(source.basis_value for source in sources)
    standard_allocations = allocate_processing_cost_amount(
        cost_group.standard_amount,
        [source.basis_value for source in sources],
    )
    actual_allocations = allocate_processing_cost_amount(
        cost_group.actual_amount,
        [source.basis_value for source in sources],
    )

    for index, source in enumerate(sources):
        ratio = (
            (source.basis_value / total_basis).quantize(Decimal("0.00000001"))
            if total_basis > 0
            else Decimal("0")
        )

        db.add(
            OutsourceProcessingCostAllocation(
                outsource_processing_cost_group_id=cost_group.outsource_processing_cost_group_id,
                outsource_work_group_id=source.work_group.outsource_work_group_id
                if source.work_group
                else None,
                outsource_work_group_item_id=source.work_group_item.outsource_work_group_item_id
                if source.work_group_item
                else None,
                lot_id=source.lot.lot_id,
                lot_no_snapshot=source.lot.lot_no,
                product_code_snapshot=source.product.product_code,
                product_name_snapshot=source.product.product_name,
                product_spec_snapshot=source.product.product_spec,
                panel_width_mm_snapshot=source.product.panel_width_mm,
                panel_length_mm_snapshot=source.product.panel_length_mm,
                cuts_per_sheet_snapshot=source.cuts_per_sheet,
                sheet_qty_snapshot=source.sheet_qty,
                instruction_output_qty_snapshot=source.instruction_output_qty,
                basis_type=source.basis_type,
                basis_value=source.basis_value,
                basis_area_sqm=source.basis_area_sqm,
                allocation_ratio=ratio,
                standard_allocated_amount=standard_allocations[index],
                actual_allocated_amount=actual_allocations[index],
            )
        )

    db.flush()


def recalculate_existing_allocations(
    cost_group: OutsourceProcessingCostGroup,
) -> None:
    allocations = list(cost_group.allocations)
    basis_values = [Decimal(allocation.basis_value) for allocation in allocations]
    standard_allocations = allocate_processing_cost_amount(
        cost_group.standard_amount,
        basis_values,
    )
    actual_allocations = allocate_processing_cost_amount(
        cost_group.actual_amount,
        basis_values,
    )

    for index, allocation in enumerate(allocations):
        allocation.standard_allocated_amount = standard_allocations[index]
        allocation.actual_allocated_amount = actual_allocations[index]


def allocate_processing_cost_amount(
    amount: Decimal | None,
    basis_values: list[Decimal],
) -> list[Decimal | None]:
    if amount is None:
        return [None for _ in basis_values]

    if not basis_values:
        return []

    amount = Decimal(amount).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    total_basis = sum(basis_values)

    if total_basis <= 0:
        raise HTTPException(status_code=409, detail="배부 기준값 합계가 0입니다.")

    allocated: list[Decimal] = []
    running_total = Decimal("0")

    for basis_value in basis_values[:-1]:
        value = (amount * basis_value / total_basis).quantize(
            MONEY_QUANT,
            rounding=ROUND_HALF_UP,
        )
        allocated.append(value)
        running_total += value

    allocated.append(amount - running_total)
    return allocated


def validate_allocation_sources(sources: list[AllocationSource]) -> None:
    if not sources:
        raise HTTPException(status_code=409, detail="배부할 LOT가 없습니다.")

    invalid_sources = [source for source in sources if source.basis_value <= 0]

    if invalid_sources:
        lot_nos = ", ".join(source.lot.lot_no for source in invalid_sources[:5])
        raise HTTPException(
            status_code=409,
            detail=f"제품 규격 또는 지시 산출수량이 없어 자동 면적 배부를 할 수 없습니다. LOT: {lot_nos}",
        )


def _resolve_basis(
    product: Product,
    output_qty: int | None,
) -> tuple[str, Decimal, Decimal | None]:
    area = calculate_area_basis(product, output_qty)
    return "AREA", area, area
