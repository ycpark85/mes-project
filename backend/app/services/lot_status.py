# app/services/lot_status.py
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.lot import Lot


def derive_lot_status_from_inspection_statuses(
    statuses: list[str],
) -> str | None:
    active_statuses = [status for status in statuses if status != "CANCELED"]

    if not active_statuses:
        return None

    for active_status in ("IN_PROGRESS", "RECEIVED", "WAITING"):
        if active_status in active_statuses:
            return active_status

    if all(status in {"PARTIAL_DONE", "DONE"} for status in active_statuses):
        return "DONE" if "DONE" in active_statuses else "PARTIAL_DONE"

    return None


def recalc_lot_status(db: Session, lot: Lot) -> str:
    """
    Deprecated.

    현재 LOT 상태 규칙:
    - LOT 생성 시: WAITING
    - 첫 공정 시작 시: IN_PROGRESS
    - 마지막 검수 실적 완료 시: DONE

    즉, lot.status 는 lot_step 집계 결과로 재계산하지 않는다.
    이 함수는 하위호환용으로만 남겨두며, 현재 상태를 그대로 반환한다.
    """
    return lot.status
