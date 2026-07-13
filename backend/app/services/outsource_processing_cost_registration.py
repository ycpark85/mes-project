from __future__ import annotations

from datetime import date

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.outsource_processing_cost_allocation import (
    OutsourceProcessingCostAllocation,
)
from app.models.outsource_processing_cost_group import OutsourceProcessingCostGroup
from app.models.outsource_processing_cost_work_group import (
    OutsourceProcessingCostWorkGroup,
)


ACTIVE_STATUSES = {"DRAFT", "CLOSED"}


def dedupe_positive_ids(values: list[int]) -> list[int]:
    return [value for value in dict.fromkeys(values) if value > 0]


def ensure_processing_cost_targets_available(
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


def generate_processing_cost_group_no(
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
