# app/services/lot_status.py
from __future__ import annotations

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.models.lot import Lot
from app.models.lot_step import LotStep


def recalc_lot_status(db: Session, lot: Lot) -> str:
    """
    SSOT = lot_step.status
    lot.status는 캐시(조회 최적화)로만 유지.

    규칙(MVP):
    - 하나라도 IN_PROGRESS면 LOT=IN_PROGRESS
    - 모두 DONE이면 LOT=DONE
    - 그 외(대부분 WAITING 혼재)는 LOT=WAITING

    성능 최적화:
    - COUNT(*) 대신 EXISTS로 조기 종료
    """
    # 1) IN_PROGRESS 존재?
    has_in_progress = db.execute(
        select(
            exists().where(
                (LotStep.lot_id == lot.lot_id) & (LotStep.status == "IN_PROGRESS")
            )
        )
    ).scalar_one()

    if has_in_progress:
        lot.status = "IN_PROGRESS"
        return lot.status

    # 2) DONE이 아닌 step 존재?
    has_not_done = db.execute(
        select(
            exists().where(
                (LotStep.lot_id == lot.lot_id) & (LotStep.status != "DONE")
            )
        )
    ).scalar_one()

    if not has_not_done:
        lot.status = "DONE"
        return lot.status

    lot.status = "WAITING"
    return lot.status