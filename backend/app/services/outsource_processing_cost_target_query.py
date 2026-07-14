from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal

from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from app.models.lot import Lot
from app.models.outsource_processing_cost_allocation import (
    OutsourceProcessingCostAllocation,
)
from app.models.outsource_processing_cost_group import OutsourceProcessingCostGroup
from app.models.outsource_processing_cost_work_group import (
    OutsourceProcessingCostWorkGroup,
)
from app.models.outsource_work_group import OutsourceWorkGroup
from app.models.outsource_work_group_item import OutsourceWorkGroupItem
from app.models.outsource_work_instruction import OutsourceWorkInstruction
from app.models.partner import Partner
from app.models.product import Product
from app.schemas.outsource_processing_cost import (
    OutsourceProcessingCostAllocationOut,
    OutsourceProcessingCostTargetListOut,
    OutsourceProcessingCostTargetOut,
)
from app.services.outsource_processing_cost_basis import (
    calculate_area_basis,
    resolve_instruction_output_qty,
)
from app.services.outsource_processing_cost_common import (
    has_processing_cost_variance,
    normalize_process_type,
    normalize_target_status,
)


def list_outsource_processing_cost_targets(
    db: Session,
    *,
    process_type: str,
    date_from: date | None = None,
    date_to: date | None = None,
    status: str | None = None,
    q: str | None = None,
) -> OutsourceProcessingCostTargetListOut:
    normalized_process_type = normalize_process_type(process_type)
    normalized_status = normalize_target_status(status) if status else None

    return OutsourceProcessingCostTargetListOut(
        items=_get_work_group_targets(
            db,
            normalized_process_type,
            date_from,
            date_to,
            normalized_status,
            q,
        )
    )


def _get_work_group_targets(
    db: Session,
    process_type: str,
    date_from: date | None,
    date_to: date | None,
    status: str | None,
    q: str | None,
) -> list[OutsourceProcessingCostTargetOut]:
    stmt = (
        select(OutsourceWorkGroup, OutsourceWorkInstruction, Partner)
        .join(
            OutsourceWorkInstruction,
            OutsourceWorkInstruction.outsource_work_instruction_id
            == OutsourceWorkGroup.outsource_work_instruction_id,
        )
        .join(Partner, Partner.partner_id == OutsourceWorkInstruction.partner_id)
        .order_by(
            OutsourceWorkInstruction.instruction_date.desc(),
            OutsourceWorkInstruction.instruction_no.desc(),
            OutsourceWorkGroup.group_seq.asc(),
        )
    )

    if process_type == "PRINT":
        stmt = stmt.where(OutsourceWorkGroup.process_type == process_type)

    if date_from:
        stmt = stmt.where(OutsourceWorkInstruction.instruction_date >= date_from)

    if date_to:
        stmt = stmt.where(OutsourceWorkInstruction.instruction_date <= date_to)

    if q and q.strip():
        like = f"%{q.strip()}%"
        item_exists = (
            select(OutsourceWorkGroupItem.outsource_work_group_item_id)
            .join(Lot, Lot.lot_id == OutsourceWorkGroupItem.lot_id)
            .join(Product, Product.product_id == Lot.product_id)
            .where(
                OutsourceWorkGroupItem.outsource_work_group_id
                == OutsourceWorkGroup.outsource_work_group_id
            )
            .where(
                (Lot.lot_no.like(like))
                | (Product.product_code.ilike(like))
                | (Product.product_name.ilike(like))
            )
            .limit(1)
        )
        stmt = stmt.where(
            (OutsourceWorkInstruction.instruction_no.like(like))
            | (Partner.name.ilike(like))
            | exists(item_exists)
        )

    rows = db.execute(stmt).all()
    work_group_ids = [
        work_group.outsource_work_group_id
        for work_group, _, _ in rows
    ]
    item_rows_by_group_id = _get_work_group_item_rows_by_group_ids(
        db,
        work_group_ids,
    )
    cost_groups_by_work_group_id = _get_target_cost_groups_by_work_group_ids(
        db,
        process_type,
        work_group_ids,
        include_canceled=status == "CANCELED",
    )
    allocation_amounts_by_target = _get_allocation_amounts_by_target(
        db,
        cost_groups_by_work_group_id,
    )
    targets: list[OutsourceProcessingCostTargetOut] = []

    for work_group, instruction, partner in rows:
        work_group_id = work_group.outsource_work_group_id
        item_rows = item_rows_by_group_id.get(work_group_id, [])
        if not item_rows:
            continue

        basis_total = Decimal("0")
        output_total = 0
        lot_nos: list[str] = []
        product_names: list[str] = []
        product_specs: list[str] = []

        for group_item, lot, product in item_rows:
            output_qty = resolve_instruction_output_qty(work_group, group_item, lot)
            output_total += output_qty or 0
            lot_nos.append(lot.lot_no)
            product_names.append(product.product_name)
            product_specs.append(_build_product_spec_text(product))

            basis_total += calculate_area_basis(product, output_qty)

        representative_row = next(
            (
                row
                for row in item_rows
                if row[1].lot_id == work_group.representative_lot_id
            ),
            item_rows[0],
        )
        representative_lot = representative_row[1]
        representative_product = representative_row[2]
        representative_product_name = representative_product.product_name
        display_product_names = (
            [representative_product_name]
            if representative_product_name
            else list(dict.fromkeys(product_names))
        )
        target_allocations = _build_target_allocation_preview(
            item_rows,
            work_group,
            basis_total,
        )

        cost_group = cost_groups_by_work_group_id.get(work_group_id)

        if not _matches_target_status(cost_group, status):
            continue

        targets.append(
            OutsourceProcessingCostTargetOut(
                target_key=f"WG:{work_group.outsource_work_group_id}",
                process_type=process_type,
                outsource_work_group_id=work_group.outsource_work_group_id,
                instruction_no=instruction.instruction_no,
                instruction_date=instruction.instruction_date,
                partner_name=partner.name,
                group_seq=work_group.group_seq,
                is_bundle=work_group.is_bundle,
                lot_count=len(item_rows),
                representative_lot_id=representative_lot.lot_id,
                representative_lot_no=representative_lot.lot_no,
                representative_product_name=representative_product_name,
                lot_nos=lot_nos,
                product_names=display_product_names,
                product_specs=list(dict.fromkeys(spec for spec in product_specs if spec)),
                sheet_qty=work_group.sheet_qty,
                instruction_output_qty=output_total,
                allocation_basis_type="AREA",
                allocation_basis_value=basis_total,
                allocations=target_allocations,
                **_build_target_cost_fields_from_amounts(
                    cost_group,
                    allocation_amounts_by_target.get(
                        (
                            cost_group.outsource_processing_cost_group_id,
                            work_group_id,
                        )
                        if cost_group is not None
                        else None
                    ),
                ),
            )
        )

    return targets


def _get_work_group_item_rows_by_group_ids(
    db: Session,
    work_group_ids: list[int],
) -> dict[int, list[tuple[OutsourceWorkGroupItem, Lot, Product]]]:
    if not work_group_ids:
        return {}

    rows = db.execute(
        select(OutsourceWorkGroupItem, Lot, Product)
        .join(Lot, Lot.lot_id == OutsourceWorkGroupItem.lot_id)
        .join(Product, Product.product_id == Lot.product_id)
        .where(OutsourceWorkGroupItem.outsource_work_group_id.in_(work_group_ids))
        .order_by(
            OutsourceWorkGroupItem.outsource_work_group_id.asc(),
            Lot.lot_no.asc(),
            OutsourceWorkGroupItem.outsource_work_group_item_id.asc(),
        )
    ).all()
    result = defaultdict(list)

    for row in rows:
        result[row[0].outsource_work_group_id].append(row)

    return dict(result)


def _get_target_cost_groups_by_work_group_ids(
    db: Session,
    process_type: str,
    work_group_ids: list[int],
    *,
    include_canceled: bool,
) -> dict[int, OutsourceProcessingCostGroup]:
    if not work_group_ids:
        return {}

    stmt = (
        select(
            OutsourceProcessingCostWorkGroup.outsource_work_group_id,
            OutsourceProcessingCostGroup,
        )
        .join(
            OutsourceProcessingCostGroup,
            OutsourceProcessingCostGroup.outsource_processing_cost_group_id
            == OutsourceProcessingCostWorkGroup.outsource_processing_cost_group_id,
        )
        .where(
            OutsourceProcessingCostGroup.process_type == process_type,
            OutsourceProcessingCostWorkGroup.outsource_work_group_id.in_(
                work_group_ids
            ),
        )
        .order_by(
            OutsourceProcessingCostWorkGroup.outsource_work_group_id.asc(),
            OutsourceProcessingCostGroup.created_at.desc(),
            OutsourceProcessingCostGroup.outsource_processing_cost_group_id.desc(),
        )
    )

    if not include_canceled:
        stmt = stmt.where(OutsourceProcessingCostGroup.status != "CANCELED")

    result: dict[int, OutsourceProcessingCostGroup] = {}
    for work_group_id, cost_group in db.execute(stmt):
        result.setdefault(work_group_id, cost_group)

    return result


def _get_allocation_amounts_by_target(
    db: Session,
    cost_groups_by_work_group_id: dict[int, OutsourceProcessingCostGroup],
) -> dict[tuple[int, int], tuple[Decimal | None, Decimal | None]]:
    if not cost_groups_by_work_group_id:
        return {}

    target_pairs = {
        (cost_group.outsource_processing_cost_group_id, work_group_id)
        for work_group_id, cost_group in cost_groups_by_work_group_id.items()
    }
    cost_group_ids = {cost_group_id for cost_group_id, _ in target_pairs}
    work_group_ids = {work_group_id for _, work_group_id in target_pairs}
    rows = db.execute(
        select(
            OutsourceProcessingCostAllocation.outsource_processing_cost_group_id,
            OutsourceProcessingCostAllocation.outsource_work_group_id,
            func.sum(OutsourceProcessingCostAllocation.standard_allocated_amount),
            func.sum(OutsourceProcessingCostAllocation.actual_allocated_amount),
        )
        .where(
            OutsourceProcessingCostAllocation.outsource_processing_cost_group_id.in_(
                cost_group_ids
            ),
            OutsourceProcessingCostAllocation.outsource_work_group_id.in_(
                work_group_ids
            ),
        )
        .group_by(
            OutsourceProcessingCostAllocation.outsource_processing_cost_group_id,
            OutsourceProcessingCostAllocation.outsource_work_group_id,
        )
    )

    return {
        (cost_group_id, work_group_id): (standard_amount, actual_amount)
        for cost_group_id, work_group_id, standard_amount, actual_amount in rows
        if (cost_group_id, work_group_id) in target_pairs
    }


def _build_target_cost_fields_from_amounts(
    cost_group: OutsourceProcessingCostGroup | None,
    amounts: tuple[Decimal | None, Decimal | None] | None,
) -> dict:
    if cost_group is None:
        return {
            "outsource_processing_cost_group_id": None,
            "already_cost_group_no": None,
            "cost_status": None,
            "standard_amount": None,
            "actual_amount": None,
            "amount_difference": None,
            "settlement_month": None,
        }

    standard_amount, actual_amount = amounts or (None, None)
    difference = (
        actual_amount - standard_amount
        if actual_amount is not None and standard_amount is not None
        else None
    )

    return {
        "outsource_processing_cost_group_id": cost_group.outsource_processing_cost_group_id,
        "already_cost_group_no": cost_group.cost_group_no,
        "cost_status": cost_group.status,
        "standard_amount": standard_amount,
        "actual_amount": actual_amount,
        "amount_difference": difference,
        "settlement_month": cost_group.settlement_month,
    }


def _build_target_allocation_preview(
    item_rows: list[tuple[OutsourceWorkGroupItem, Lot, Product]],
    work_group: OutsourceWorkGroup,
    basis_total: Decimal,
) -> list[OutsourceProcessingCostAllocationOut]:
    items: list[OutsourceProcessingCostAllocationOut] = []

    for group_item, lot, product in item_rows:
        output_qty = resolve_instruction_output_qty(work_group, group_item, lot)
        basis_value = calculate_area_basis(product, output_qty)
        ratio = (
            (basis_value / basis_total).quantize(Decimal("0.00000001"))
            if basis_total > 0
            else Decimal("0")
        )

        items.append(
            OutsourceProcessingCostAllocationOut(
                lot_id=lot.lot_id,
                lot_no=lot.lot_no,
                product_code=product.product_code,
                product_name=product.product_name,
                product_spec=product.product_spec,
                panel_width_mm=product.panel_width_mm,
                panel_length_mm=product.panel_length_mm,
                cuts_per_sheet=group_item.cuts_per_sheet,
                sheet_qty=work_group.sheet_qty,
                instruction_output_qty=output_qty,
                basis_type="AREA",
                basis_value=basis_value,
                basis_area_sqm=basis_value,
                allocation_ratio=ratio,
                standard_allocated_amount=None,
                actual_allocated_amount=None,
                amount_difference=None,
            )
        )

    return items


def find_target_cost_group_for_work_group(
    db: Session,
    process_type: str,
    work_group_id: int,
    *,
    include_canceled: bool = False,
) -> OutsourceProcessingCostGroup | None:
    stmt = (
        select(OutsourceProcessingCostGroup)
        .join(
            OutsourceProcessingCostWorkGroup,
            OutsourceProcessingCostWorkGroup.outsource_processing_cost_group_id
            == OutsourceProcessingCostGroup.outsource_processing_cost_group_id,
        )
        .where(OutsourceProcessingCostGroup.process_type == process_type)
        .where(OutsourceProcessingCostWorkGroup.outsource_work_group_id == work_group_id)
        .order_by(
            OutsourceProcessingCostGroup.created_at.desc(),
            OutsourceProcessingCostGroup.outsource_processing_cost_group_id.desc(),
        )
        .limit(1)
    )

    if not include_canceled:
        stmt = stmt.where(OutsourceProcessingCostGroup.status != "CANCELED")

    return db.execute(stmt).scalar_one_or_none()


def build_target_cost_fields(
    db: Session,
    cost_group: OutsourceProcessingCostGroup | None,
    work_group_id: int,
) -> dict:
    if cost_group is None:
        return {
            "outsource_processing_cost_group_id": None,
            "already_cost_group_no": None,
            "cost_status": None,
            "standard_amount": None,
            "actual_amount": None,
            "amount_difference": None,
            "settlement_month": None,
        }

    standard_amount, actual_amount = (
        db.execute(
            select(
                func.sum(OutsourceProcessingCostAllocation.standard_allocated_amount),
                func.sum(OutsourceProcessingCostAllocation.actual_allocated_amount),
            )
            .where(
                OutsourceProcessingCostAllocation.outsource_processing_cost_group_id
                == cost_group.outsource_processing_cost_group_id,
                OutsourceProcessingCostAllocation.outsource_work_group_id == work_group_id,
            )
        )
        .one()
    )

    difference = (
        actual_amount - standard_amount
        if actual_amount is not None and standard_amount is not None
        else None
    )

    return {
        "outsource_processing_cost_group_id": cost_group.outsource_processing_cost_group_id,
        "already_cost_group_no": cost_group.cost_group_no,
        "cost_status": cost_group.status,
        "standard_amount": standard_amount,
        "actual_amount": actual_amount,
        "amount_difference": difference,
        "settlement_month": cost_group.settlement_month,
    }


def _matches_target_status(
    cost_group: OutsourceProcessingCostGroup | None,
    status: str | None,
) -> bool:
    if status is None:
        return True

    if status == "UNREGISTERED":
        return cost_group is None

    if status == "COST_VARIANCE":
        return cost_group is not None and has_processing_cost_variance(cost_group)

    return cost_group is not None and cost_group.status == status


def _build_product_spec_text(product: Product) -> str:
    if product.panel_width_mm and product.panel_length_mm:
        return f"{product.panel_width_mm}x{product.panel_length_mm}"

    return product.product_spec or ""
