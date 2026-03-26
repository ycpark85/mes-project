# app/services/lot_status.py
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.lot import Lot


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