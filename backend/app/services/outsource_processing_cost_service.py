from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.time import utc_now

from app.models.outsource_processing_cost_group import OutsourceProcessingCostGroup
from app.models.outsource_processing_cost_work_group import (
    OutsourceProcessingCostWorkGroup,
)
from app.schemas.outsource_processing_cost import (
    OutsourceProcessingCostCreate,
    OutsourceProcessingCostUpdate,
)
from app.services.outsource_processing_cost_allocation_service import (
    build_allocation_sources,
    recalculate_existing_allocations,
    replace_processing_cost_allocations,
)
from app.services.outsource_processing_cost_common import (
    normalize_month,
    normalize_process_type,
)
from app.services.outsource_processing_cost_registration import (
    dedupe_positive_ids,
    ensure_processing_cost_targets_available,
    generate_processing_cost_group_no,
)


def create_processing_cost_group(
    db: Session,
    payload: OutsourceProcessingCostCreate,
) -> OutsourceProcessingCostGroup:
    process_type = normalize_process_type(payload.process_type)
    settlement_month = normalize_month(payload.settlement_month)
    target_work_group_ids = dedupe_positive_ids(payload.target_work_group_ids)
    target_lot_ids = dedupe_positive_ids(payload.target_lot_ids)

    if not target_work_group_ids and not target_lot_ids:
        raise HTTPException(status_code=409, detail="가공비 등록 대상이 없습니다.")

    if target_lot_ids:
        raise HTTPException(status_code=409, detail="재단/인쇄는 외주작업 묶음 기준으로 등록해야 합니다.")

    if not target_work_group_ids:
        raise HTTPException(status_code=409, detail="외주작업 묶음을 선택하세요.")

    ensure_processing_cost_targets_available(
        db,
        process_type,
        target_work_group_ids,
        target_lot_ids,
    )

    sources = build_allocation_sources(
        db,
        process_type,
        target_work_group_ids,
        target_lot_ids,
    )

    cost_group = OutsourceProcessingCostGroup(
        cost_group_no=generate_processing_cost_group_no(
            db,
            process_type,
            settlement_month,
        ),
        settlement_month=settlement_month,
        process_type=process_type,
        status="DRAFT",
        standard_amount=payload.standard_amount,
        standard_memo=payload.standard_memo,
        actual_amount=payload.actual_amount,
        actual_billing_month=normalize_month(payload.actual_billing_month)
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

    replace_processing_cost_allocations(db, cost_group, sources)

    return cost_group


def get_processing_cost_group_or_404(
    db: Session,
    cost_group_id: int,
) -> OutsourceProcessingCostGroup:
    cost_group = db.get(OutsourceProcessingCostGroup, cost_group_id)

    if cost_group is None:
        raise HTTPException(status_code=404, detail="가공비 묶음을 찾을 수 없습니다.")

    return cost_group


def ensure_processing_cost_group_editable(
    cost_group: OutsourceProcessingCostGroup,
) -> None:
    if cost_group.status == "CLOSED":
        raise HTTPException(status_code=409, detail="마감된 가공비 묶음은 수정할 수 없습니다.")

    if cost_group.status == "CANCELED":
        raise HTTPException(status_code=409, detail="취소된 가공비 묶음은 수정할 수 없습니다.")


def update_processing_cost_group(
    db: Session,
    cost_group_id: int,
    payload: OutsourceProcessingCostUpdate,
) -> OutsourceProcessingCostGroup:
    cost_group = get_processing_cost_group_or_404(db, cost_group_id)
    ensure_processing_cost_group_editable(cost_group)

    cost_group.standard_amount = payload.standard_amount
    cost_group.standard_memo = payload.standard_memo
    cost_group.actual_amount = payload.actual_amount
    cost_group.actual_billing_month = (
        normalize_month(payload.actual_billing_month)
        if payload.actual_billing_month
        else None
    )
    cost_group.actual_memo = payload.actual_memo
    cost_group.remark = payload.remark

    recalculate_existing_allocations(cost_group)

    return cost_group


def close_processing_cost_group(
    db: Session,
    cost_group_id: int,
) -> OutsourceProcessingCostGroup:
    cost_group = get_processing_cost_group_or_404(db, cost_group_id)

    if cost_group.status == "CANCELED":
        raise HTTPException(status_code=409, detail="취소된 가공비 묶음은 마감할 수 없습니다.")

    if cost_group.actual_amount is None:
        raise HTTPException(status_code=409, detail="실제가공비 입력 후 마감할 수 있습니다.")

    cost_group.status = "CLOSED"
    cost_group.closed_at = utc_now()

    return cost_group


def reopen_processing_cost_group(
    db: Session,
    cost_group_id: int,
) -> OutsourceProcessingCostGroup:
    cost_group = get_processing_cost_group_or_404(db, cost_group_id)

    if cost_group.status != "CLOSED":
        raise HTTPException(status_code=409, detail="마감 상태만 마감취소할 수 있습니다.")

    cost_group.status = "DRAFT"
    cost_group.closed_at = None

    return cost_group


def cancel_processing_cost_group(
    db: Session,
    cost_group_id: int,
) -> OutsourceProcessingCostGroup:
    cost_group = get_processing_cost_group_or_404(db, cost_group_id)

    if cost_group.status == "CANCELED":
        return cost_group

    cost_group.status = "CANCELED"
    cost_group.canceled_at = utc_now()

    return cost_group
