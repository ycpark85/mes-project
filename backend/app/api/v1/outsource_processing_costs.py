from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.outsource_processing_cost import (
    OutsourceProcessingCostCreate,
    OutsourceProcessingCostGroupListItemOut,
    OutsourceProcessingCostGroupListOut,
    OutsourceProcessingCostTargetListOut,
    OutsourceProcessingCostUpdate,
)
from app.services.outsource_processing_cost_group_query import (
    build_processing_cost_group_out,
    list_outsource_processing_cost_groups as list_outsource_processing_cost_groups_service,
)
from app.services.outsource_processing_cost_target_query import (
    list_outsource_processing_cost_targets as list_outsource_processing_cost_targets_service,
)
from app.services.outsource_processing_cost_service import (
    cancel_processing_cost_group as cancel_processing_cost_group_service,
    close_processing_cost_group as close_processing_cost_group_service,
    create_processing_cost_group as create_processing_cost_group_service,
    reopen_processing_cost_group as reopen_processing_cost_group_service,
    update_processing_cost_group as update_processing_cost_group_service,
)

router = APIRouter(
    prefix="/outsource-processing-costs",
    tags=["OutsourceProcessingCosts"],
)


def _commit_processing_cost_group_change(
    db: Session,
    cost_group,
) -> OutsourceProcessingCostGroupListItemOut:
    db.commit()
    db.refresh(cost_group)

    return build_processing_cost_group_out(db, cost_group)


@router.get("/targets", response_model=OutsourceProcessingCostTargetListOut)
def get_outsource_processing_cost_targets(
    process_type: str = Query(...),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    status: str | None = Query(default=None),
    q: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return list_outsource_processing_cost_targets_service(
        db,
        process_type=process_type,
        date_from=date_from,
        date_to=date_to,
        status=status,
        q=q,
        page=page,
        size=size,
    )


@router.get("", response_model=OutsourceProcessingCostGroupListOut)
def list_outsource_processing_cost_groups(
    settlement_month: date | None = Query(default=None),
    process_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    q: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return list_outsource_processing_cost_groups_service(
        db,
        settlement_month=settlement_month,
        process_type=process_type,
        status=status,
        q=q,
    )


@router.post("", response_model=OutsourceProcessingCostGroupListItemOut)
def create_outsource_processing_cost_group(
    payload: OutsourceProcessingCostCreate,
    db: Session = Depends(get_db),
):
    cost_group = create_processing_cost_group_service(db, payload)
    return _commit_processing_cost_group_change(db, cost_group)


@router.patch("/{cost_group_id}", response_model=OutsourceProcessingCostGroupListItemOut)
def update_outsource_processing_cost_group(
    cost_group_id: int,
    payload: OutsourceProcessingCostUpdate,
    db: Session = Depends(get_db),
):
    cost_group = update_processing_cost_group_service(db, cost_group_id, payload)
    return _commit_processing_cost_group_change(db, cost_group)


@router.post("/{cost_group_id}/close", response_model=OutsourceProcessingCostGroupListItemOut)
def close_outsource_processing_cost_group(
    cost_group_id: int,
    db: Session = Depends(get_db),
):
    cost_group = close_processing_cost_group_service(db, cost_group_id)
    return _commit_processing_cost_group_change(db, cost_group)


@router.post("/{cost_group_id}/reopen", response_model=OutsourceProcessingCostGroupListItemOut)
def reopen_outsource_processing_cost_group(
    cost_group_id: int,
    db: Session = Depends(get_db),
):
    cost_group = reopen_processing_cost_group_service(db, cost_group_id)
    return _commit_processing_cost_group_change(db, cost_group)


@router.post("/{cost_group_id}/cancel", response_model=OutsourceProcessingCostGroupListItemOut)
def cancel_outsource_processing_cost_group(
    cost_group_id: int,
    db: Session = Depends(get_db),
):
    cost_group = cancel_processing_cost_group_service(db, cost_group_id)
    return _commit_processing_cost_group_change(db, cost_group)
