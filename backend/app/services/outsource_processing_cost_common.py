from __future__ import annotations

from datetime import date

from fastapi import HTTPException

from app.models.outsource_processing_cost_group import OutsourceProcessingCostGroup


PROCESS_TYPES = {"CUT", "PRINT", "DIECUT"}


def has_processing_cost_variance(cost_group: OutsourceProcessingCostGroup) -> bool:
    return (
        cost_group.status == "DRAFT"
        and cost_group.standard_amount is not None
        and cost_group.actual_amount is not None
        and cost_group.actual_amount != cost_group.standard_amount
    )


def normalize_process_type(process_type: str | None) -> str:
    normalized = (process_type or "").strip().upper()

    if normalized not in PROCESS_TYPES:
        raise HTTPException(status_code=409, detail="Invalid process_type")

    return normalized


def normalize_status(status: str | None) -> str:
    normalized = (status or "").strip().upper()

    if normalized not in {"DRAFT", "CLOSED", "CANCELED", "COST_VARIANCE"}:
        raise HTTPException(status_code=409, detail="Invalid status")

    return normalized


def normalize_target_status(status: str | None) -> str:
    normalized = (status or "").strip().upper()

    if normalized not in {"UNREGISTERED", "DRAFT", "CLOSED", "CANCELED", "COST_VARIANCE"}:
        raise HTTPException(status_code=409, detail="Invalid status")

    return normalized


def normalize_month(value: date) -> date:
    return date(value.year, value.month, 1)
