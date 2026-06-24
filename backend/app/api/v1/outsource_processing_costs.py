from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import exists, func, or_, select
from sqlalchemy.orm import Session

from app.db.session import get_db
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
    OutsourceProcessingCostCreate,
    OutsourceProcessingCostGroupListItemOut,
    OutsourceProcessingCostGroupListOut,
    OutsourceProcessingCostTargetListOut,
    OutsourceProcessingCostTargetOut,
    OutsourceProcessingCostUpdate,
)

router = APIRouter(
    prefix="/outsource-processing-costs",
    tags=["OutsourceProcessingCosts"],
)

PROCESS_TYPES = {"CUT", "PRINT", "DIECUT"}
ACTIVE_STATUSES = {"DRAFT", "CLOSED"}
MONEY_QUANT = Decimal("1")


@dataclass
class _AllocationSource:
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


@router.get("/targets", response_model=OutsourceProcessingCostTargetListOut)
def get_outsource_processing_cost_targets(
    process_type: str = Query(...),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    status: str | None = Query(default=None),
    q: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    normalized_process_type = _normalize_process_type(process_type)
    normalized_status = _normalize_target_status(status) if status else None

    return OutsourceProcessingCostTargetListOut(
        items=_get_work_group_targets(db, normalized_process_type, date_from, date_to, normalized_status, q)
    )


@router.get("", response_model=OutsourceProcessingCostGroupListOut)
def list_outsource_processing_cost_groups(
    settlement_month: date | None = Query(default=None),
    process_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    q: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    normalized_process_type = _normalize_process_type(process_type) if process_type else None
    normalized_status = _normalize_status(status) if status else None
    normalized_month = _normalize_month(settlement_month) if settlement_month else None

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
    items = [_build_group_out(db, group) for group in groups]

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


@router.post("", response_model=OutsourceProcessingCostGroupListItemOut)
def create_outsource_processing_cost_group(
    payload: OutsourceProcessingCostCreate,
    db: Session = Depends(get_db),
):
    process_type = _normalize_process_type(payload.process_type)
    settlement_month = _normalize_month(payload.settlement_month)
    target_work_group_ids = _dedupe_positive_ids(payload.target_work_group_ids)
    target_lot_ids = _dedupe_positive_ids(payload.target_lot_ids)

    if not target_work_group_ids and not target_lot_ids:
        raise HTTPException(status_code=409, detail="가공비 등록 대상이 없습니다.")

    if target_lot_ids:
        raise HTTPException(status_code=409, detail="재단/인쇄는 외주작업 묶음 기준으로 등록해야 합니다.")

    if not target_work_group_ids:
        raise HTTPException(status_code=409, detail="외주작업 묶음을 선택하세요.")

    _ensure_targets_not_in_active_cost_group(
        db,
        process_type,
        target_work_group_ids,
        target_lot_ids,
    )

    sources = _build_allocation_sources(
        db,
        process_type,
        target_work_group_ids,
        target_lot_ids,
    )
    _validate_sources(process_type, sources)

    cost_group = OutsourceProcessingCostGroup(
        cost_group_no=_generate_cost_group_no(db, process_type, settlement_month),
        settlement_month=settlement_month,
        process_type=process_type,
        status="DRAFT",
        standard_amount=payload.standard_amount,
        standard_memo=payload.standard_memo,
        actual_amount=payload.actual_amount,
        actual_billing_month=_normalize_month(payload.actual_billing_month)
        if payload.actual_billing_month
        else None,
        actual_memo=payload.actual_memo,
        remark=payload.remark,
    )
    db.add(cost_group)
    db.flush()

    for work_group_id in target_work_group_ids:
        db.add(
            OutsourceProcessingCostWorkGroup(
                outsource_processing_cost_group_id=cost_group.outsource_processing_cost_group_id,
                outsource_work_group_id=work_group_id,
            )
        )

    _replace_allocations(db, cost_group, sources)
    db.commit()
    db.refresh(cost_group)

    return _build_group_out(db, cost_group)


@router.patch("/{cost_group_id}", response_model=OutsourceProcessingCostGroupListItemOut)
def update_outsource_processing_cost_group(
    cost_group_id: int,
    payload: OutsourceProcessingCostUpdate,
    db: Session = Depends(get_db),
):
    cost_group = _get_cost_group_or_404(db, cost_group_id)
    _ensure_editable(cost_group)

    cost_group.standard_amount = payload.standard_amount
    cost_group.standard_memo = payload.standard_memo
    cost_group.actual_amount = payload.actual_amount
    cost_group.actual_billing_month = (
        _normalize_month(payload.actual_billing_month)
        if payload.actual_billing_month
        else None
    )
    cost_group.actual_memo = payload.actual_memo
    cost_group.remark = payload.remark

    _recalculate_existing_allocations(cost_group)
    db.commit()
    db.refresh(cost_group)

    return _build_group_out(db, cost_group)


@router.post("/{cost_group_id}/close", response_model=OutsourceProcessingCostGroupListItemOut)
def close_outsource_processing_cost_group(
    cost_group_id: int,
    db: Session = Depends(get_db),
):
    cost_group = _get_cost_group_or_404(db, cost_group_id)

    if cost_group.status == "CANCELED":
        raise HTTPException(status_code=409, detail="취소된 가공비 묶음은 월마감할 수 없습니다.")

    if cost_group.actual_amount is None:
        raise HTTPException(status_code=409, detail="실제가공비 입력 후 월마감할 수 있습니다.")

    cost_group.status = "CLOSED"
    cost_group.closed_at = datetime.now()
    db.commit()
    db.refresh(cost_group)

    return _build_group_out(db, cost_group)


@router.post("/{cost_group_id}/reopen", response_model=OutsourceProcessingCostGroupListItemOut)
def reopen_outsource_processing_cost_group(
    cost_group_id: int,
    db: Session = Depends(get_db),
):
    cost_group = _get_cost_group_or_404(db, cost_group_id)

    if cost_group.status != "CLOSED":
        raise HTTPException(status_code=409, detail="월마감 상태만 마감취소할 수 있습니다.")

    cost_group.status = "DRAFT"
    cost_group.closed_at = None
    db.commit()
    db.refresh(cost_group)

    return _build_group_out(db, cost_group)


@router.post("/{cost_group_id}/cancel", response_model=OutsourceProcessingCostGroupListItemOut)
def cancel_outsource_processing_cost_group(
    cost_group_id: int,
    db: Session = Depends(get_db),
):
    cost_group = _get_cost_group_or_404(db, cost_group_id)

    if cost_group.status == "CANCELED":
        return _build_group_out(db, cost_group)

    cost_group.status = "CANCELED"
    cost_group.canceled_at = datetime.now()
    db.commit()
    db.refresh(cost_group)

    return _build_group_out(db, cost_group)


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
                | (Product.product_code.like(like))
                | (Product.product_name.like(like))
            )
            .limit(1)
        )
        stmt = stmt.where(
            (OutsourceWorkInstruction.instruction_no.like(like))
            | (Partner.name.like(like))
            | exists(item_exists)
        )

    rows = db.execute(stmt).all()
    targets: list[OutsourceProcessingCostTargetOut] = []

    for work_group, instruction, partner in rows:
        item_rows = _get_work_group_item_rows(db, work_group.outsource_work_group_id)
        if not item_rows:
            continue

        basis_total = Decimal("0")
        output_total = 0
        lot_nos: list[str] = []
        product_names: list[str] = []
        product_specs: list[str] = []

        for group_item, lot, product in item_rows:
            output_qty = _resolve_instruction_output_qty(work_group, group_item, lot)
            output_total += output_qty or 0
            lot_nos.append(lot.lot_no)
            product_names.append(product.product_name)
            product_specs.append(_build_product_spec_text(product))

            basis_total += _calculate_area_basis(product, output_qty)

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
        target_allocations = _build_target_allocation_preview(item_rows, work_group, basis_total)

        cost_group = _find_target_cost_group_for_work_group(
            db,
            process_type,
            work_group.outsource_work_group_id,
        )

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
                **_build_target_cost_fields(cost_group),
            )
        )

    return targets


def _build_allocation_sources(
    db: Session,
    process_type: str,
    work_group_ids: list[int],
    lot_ids: list[int],
) -> list[_AllocationSource]:
    sources: list[_AllocationSource] = []

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

            for group_item, lot, product in _get_work_group_item_rows(
                db,
                work_group.outsource_work_group_id,
            ):
                output_qty = _resolve_instruction_output_qty(work_group, group_item, lot)
                basis_type, basis_value, basis_area_sqm = _resolve_basis(
                    process_type,
                    product,
                    output_qty,
                )
                sources.append(
                    _AllocationSource(
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
                process_type,
                product,
                lot.lot_qty,
            )
            sources.append(
                _AllocationSource(
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

    return sources


def _build_target_allocation_preview(
    item_rows: list[tuple[OutsourceWorkGroupItem, Lot, Product]],
    work_group: OutsourceWorkGroup,
    basis_total: Decimal,
) -> list[OutsourceProcessingCostAllocationOut]:
    items: list[OutsourceProcessingCostAllocationOut] = []

    for group_item, lot, product in item_rows:
        output_qty = _resolve_instruction_output_qty(work_group, group_item, lot)
        basis_value = _calculate_area_basis(product, output_qty)
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


def _replace_allocations(
    db: Session,
    cost_group: OutsourceProcessingCostGroup,
    sources: list[_AllocationSource],
) -> None:
    for allocation in list(cost_group.allocations):
        db.delete(allocation)

    total_basis = sum(source.basis_value for source in sources)
    standard_allocations = _allocate_amount(cost_group.standard_amount, sources)
    actual_allocations = _allocate_amount(cost_group.actual_amount, sources)

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


def _recalculate_existing_allocations(cost_group: OutsourceProcessingCostGroup) -> None:
    allocations = list(cost_group.allocations)
    sources = [
        _AllocationSource(
            lot=allocation.lot,
            product=allocation.lot.product,
            work_group=allocation.work_group,
            work_group_item=allocation.work_group_item,
            cuts_per_sheet=allocation.cuts_per_sheet_snapshot,
            sheet_qty=allocation.sheet_qty_snapshot,
            instruction_output_qty=allocation.instruction_output_qty_snapshot,
            basis_type=allocation.basis_type,
            basis_value=Decimal(allocation.basis_value),
            basis_area_sqm=allocation.basis_area_sqm,
        )
        for allocation in allocations
    ]
    standard_allocations = _allocate_amount(cost_group.standard_amount, sources)
    actual_allocations = _allocate_amount(cost_group.actual_amount, sources)

    for index, allocation in enumerate(allocations):
        allocation.standard_allocated_amount = standard_allocations[index]
        allocation.actual_allocated_amount = actual_allocations[index]


def _allocate_amount(
    amount: Decimal | None,
    sources: list[_AllocationSource],
) -> list[Decimal | None]:
    if amount is None:
        return [None for _ in sources]

    if not sources:
        return []

    amount = Decimal(amount).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    total_basis = sum(source.basis_value for source in sources)

    if total_basis <= 0:
        raise HTTPException(status_code=409, detail="배부 기준값 합계가 0입니다.")

    allocated: list[Decimal] = []
    running_total = Decimal("0")

    for source in sources[:-1]:
        value = (amount * source.basis_value / total_basis).quantize(
            MONEY_QUANT,
            rounding=ROUND_HALF_UP,
        )
        allocated.append(value)
        running_total += value

    allocated.append(amount - running_total)
    return allocated


def _get_work_group_item_rows(
    db: Session,
    work_group_id: int,
) -> list[tuple[OutsourceWorkGroupItem, Lot, Product]]:
    return (
        db.execute(
            select(OutsourceWorkGroupItem, Lot, Product)
            .join(Lot, Lot.lot_id == OutsourceWorkGroupItem.lot_id)
            .join(Product, Product.product_id == Lot.product_id)
            .where(OutsourceWorkGroupItem.outsource_work_group_id == work_group_id)
            .order_by(Lot.lot_no.asc(), OutsourceWorkGroupItem.outsource_work_group_item_id.asc())
        )
        .all()
    )


def _resolve_instruction_output_qty(
    work_group: OutsourceWorkGroup,
    group_item: OutsourceWorkGroupItem,
    lot: Lot,
) -> int:
    if group_item.expected_output_qty is not None:
        return int(group_item.expected_output_qty)

    if work_group.sheet_qty is not None and group_item.cuts_per_sheet is not None:
        return int(work_group.sheet_qty) * int(group_item.cuts_per_sheet)

    return int(lot.lot_qty)


def _resolve_basis(
    process_type: str,
    product: Product,
    output_qty: int | None,
) -> tuple[str, Decimal, Decimal | None]:
    area = _calculate_area_basis(product, output_qty)
    return "AREA", area, area


def _calculate_area_basis(product: Product, output_qty: int | None) -> Decimal:
    if not product.panel_width_mm or not product.panel_length_mm or not output_qty:
        return Decimal("0")

    return (
        Decimal(product.panel_width_mm)
        * Decimal(product.panel_length_mm)
        * Decimal(output_qty)
        / Decimal("1000000")
    ).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)


def _build_product_spec_text(product: Product) -> str:
    if product.panel_width_mm and product.panel_length_mm:
        return f"{product.panel_width_mm}x{product.panel_length_mm}"

    return product.product_spec or ""


def _validate_sources(process_type: str, sources: list[_AllocationSource]) -> None:
    if not sources:
        raise HTTPException(status_code=409, detail="배부할 LOT가 없습니다.")

    invalid_sources = [source for source in sources if source.basis_value <= 0]

    if invalid_sources:
        lot_nos = ", ".join(source.lot.lot_no for source in invalid_sources[:5])
        raise HTTPException(
            status_code=409,
            detail=f"제품 규격 또는 지시 산출수량이 없어 자동 면적 배부를 할 수 없습니다. LOT: {lot_nos}",
        )


def _ensure_targets_not_in_active_cost_group(
    db: Session,
    process_type: str,
    work_group_ids: list[int],
    lot_ids: list[int],
) -> None:
    if work_group_ids:
        existing = (
            db.execute(
                select(OutsourceProcessingCostGroup.cost_group_no)
                .join(
                    OutsourceProcessingCostWorkGroup,
                    OutsourceProcessingCostWorkGroup.outsource_processing_cost_group_id
                    == OutsourceProcessingCostGroup.outsource_processing_cost_group_id,
                )
                .where(OutsourceProcessingCostGroup.process_type == process_type)
                .where(OutsourceProcessingCostGroup.status.in_(ACTIVE_STATUSES))
                .where(
                    OutsourceProcessingCostWorkGroup.outsource_work_group_id.in_(
                        work_group_ids
                    )
                )
                .limit(1)
            )
            .scalar_one_or_none()
        )

        if existing:
            raise HTTPException(status_code=409, detail=f"이미 비용묶음에 포함된 작업묶음입니다: {existing}")

    if lot_ids:
        existing = (
            db.execute(
                select(OutsourceProcessingCostGroup.cost_group_no)
                .join(
                    OutsourceProcessingCostAllocation,
                    OutsourceProcessingCostAllocation.outsource_processing_cost_group_id
                    == OutsourceProcessingCostGroup.outsource_processing_cost_group_id,
                )
                .where(OutsourceProcessingCostGroup.process_type == process_type)
                .where(OutsourceProcessingCostGroup.status.in_(ACTIVE_STATUSES))
                .where(OutsourceProcessingCostAllocation.lot_id.in_(lot_ids))
                .limit(1)
            )
            .scalar_one_or_none()
        )

        if existing:
            raise HTTPException(status_code=409, detail=f"이미 비용묶음에 포함된 LOT입니다. {existing}")


def _find_active_cost_group_no_for_work_group(
    db: Session,
    process_type: str,
    work_group_id: int,
) -> str | None:
    return (
        db.execute(
            select(OutsourceProcessingCostGroup.cost_group_no)
            .join(
                OutsourceProcessingCostWorkGroup,
                OutsourceProcessingCostWorkGroup.outsource_processing_cost_group_id
                == OutsourceProcessingCostGroup.outsource_processing_cost_group_id,
            )
            .where(OutsourceProcessingCostGroup.process_type == process_type)
            .where(OutsourceProcessingCostGroup.status.in_(ACTIVE_STATUSES))
            .where(OutsourceProcessingCostWorkGroup.outsource_work_group_id == work_group_id)
            .limit(1)
        )
        .scalar_one_or_none()
    )


def _find_active_cost_group_no_for_lot(
    db: Session,
    process_type: str,
    lot_id: int,
) -> str | None:
    return (
        db.execute(
            select(OutsourceProcessingCostGroup.cost_group_no)
            .join(
                OutsourceProcessingCostAllocation,
                OutsourceProcessingCostAllocation.outsource_processing_cost_group_id
                == OutsourceProcessingCostGroup.outsource_processing_cost_group_id,
            )
            .where(OutsourceProcessingCostGroup.process_type == process_type)
            .where(OutsourceProcessingCostGroup.status.in_(ACTIVE_STATUSES))
            .where(OutsourceProcessingCostAllocation.lot_id == lot_id)
            .limit(1)
        )
        .scalar_one_or_none()
    )


def _find_target_cost_group_for_work_group(
    db: Session,
    process_type: str,
    work_group_id: int,
) -> OutsourceProcessingCostGroup | None:
    return (
        db.execute(
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
        .scalar_one_or_none()
    )


def _find_target_cost_group_for_lot(
    db: Session,
    process_type: str,
    lot_id: int,
) -> OutsourceProcessingCostGroup | None:
    return (
        db.execute(
            select(OutsourceProcessingCostGroup)
            .join(
                OutsourceProcessingCostAllocation,
                OutsourceProcessingCostAllocation.outsource_processing_cost_group_id
                == OutsourceProcessingCostGroup.outsource_processing_cost_group_id,
            )
            .where(OutsourceProcessingCostGroup.process_type == process_type)
            .where(OutsourceProcessingCostAllocation.lot_id == lot_id)
            .order_by(
                OutsourceProcessingCostGroup.created_at.desc(),
                OutsourceProcessingCostGroup.outsource_processing_cost_group_id.desc(),
            )
            .limit(1)
        )
        .scalar_one_or_none()
    )


def _matches_target_status(
    cost_group: OutsourceProcessingCostGroup | None,
    status: str | None,
) -> bool:
    if status is None:
        return True

    if status == "UNREGISTERED":
        return cost_group is None

    if status == "COST_VARIANCE":
        return cost_group is not None and _has_cost_variance(cost_group)

    return cost_group is not None and cost_group.status == status


def _has_cost_variance(cost_group: OutsourceProcessingCostGroup) -> bool:
    return (
        cost_group.status == "DRAFT"
        and cost_group.standard_amount is not None
        and cost_group.actual_amount is not None
        and cost_group.actual_amount != cost_group.standard_amount
    )


def _build_target_cost_fields(
    cost_group: OutsourceProcessingCostGroup | None,
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

    difference = (
        cost_group.actual_amount - cost_group.standard_amount
        if cost_group.actual_amount is not None and cost_group.standard_amount is not None
        else None
    )

    return {
        "outsource_processing_cost_group_id": cost_group.outsource_processing_cost_group_id,
        "already_cost_group_no": cost_group.cost_group_no,
        "cost_status": cost_group.status,
        "standard_amount": cost_group.standard_amount,
        "actual_amount": cost_group.actual_amount,
        "amount_difference": difference,
        "settlement_month": cost_group.settlement_month,
    }


def _build_group_out(
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
            select(OutsourceProcessingCostWorkGroup, OutsourceWorkGroup, OutsourceWorkInstruction, Partner)
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

    allocation_items = [_build_allocation_out(allocation) for allocation in allocations]
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


def _build_allocation_out(
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


def _generate_cost_group_no(
    db: Session,
    process_type: str,
    settlement_month: date,
) -> str:
    prefix = f"OPC-{process_type}-{settlement_month:%Y%m}-"
    count = (
        db.execute(
            select(func.count(OutsourceProcessingCostGroup.outsource_processing_cost_group_id))
            .where(OutsourceProcessingCostGroup.cost_group_no.like(f"{prefix}%"))
        )
        .scalar_one()
    )
    return f"{prefix}{int(count) + 1:04d}"


def _get_cost_group_or_404(
    db: Session,
    cost_group_id: int,
) -> OutsourceProcessingCostGroup:
    cost_group = db.get(OutsourceProcessingCostGroup, cost_group_id)

    if cost_group is None:
        raise HTTPException(status_code=404, detail="가공비 묶음을 찾을 수 없습니다.")

    return cost_group


def _ensure_editable(cost_group: OutsourceProcessingCostGroup) -> None:
    if cost_group.status == "CLOSED":
        raise HTTPException(status_code=409, detail="월마감된 가공비 묶음은 수정할 수 없습니다.")

    if cost_group.status == "CANCELED":
        raise HTTPException(status_code=409, detail="취소된 가공비 묶음은 수정할 수 없습니다.")


def _normalize_process_type(process_type: str | None) -> str:
    normalized = (process_type or "").strip().upper()

    if normalized not in PROCESS_TYPES:
        raise HTTPException(status_code=409, detail="Invalid process_type")

    return normalized


def _normalize_status(status: str | None) -> str:
    normalized = (status or "").strip().upper()

    if normalized not in {"DRAFT", "CLOSED", "CANCELED", "COST_VARIANCE"}:
        raise HTTPException(status_code=409, detail="Invalid status")

    return normalized


def _normalize_target_status(status: str | None) -> str:
    normalized = (status or "").strip().upper()

    if normalized not in {"UNREGISTERED", "DRAFT", "CLOSED", "CANCELED", "COST_VARIANCE"}:
        raise HTTPException(status_code=409, detail="Invalid status")

    return normalized


def _normalize_month(value: date) -> date:
    return date(value.year, value.month, 1)


def _dedupe_positive_ids(values: list[int]) -> list[int]:
    return [value for value in dict.fromkeys(values) if value > 0]
