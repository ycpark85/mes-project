# app/api/v1/lot_steps.py
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status as http_status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.lot_step import LotStep
from app.models.lot import Lot
from app.models.order_line import OrderLine
from app.schemas.lot import LotStepOut
from app.services.lot_status import recalc_lot_status  # 너가 만든 서비스

router = APIRouter(prefix="/lot-steps", tags=["LotStep"])


# ---------------------------
# Locking helpers (핵심)
# ---------------------------

def _lock_lot_step(db: Session, lot_step_id: int) -> LotStep:
    """
    lot_step row를 FOR UPDATE로 잠근다.
    (동시에 수정하는 요청 간 경쟁을 줄임)
    """
    step = db.execute(
        select(LotStep)
        .where(LotStep.lot_step_id == lot_step_id)
        .with_for_update()
    ).scalar_one_or_none()
    if not step:
        raise HTTPException(status_code=404, detail="LotStep not found")
    return step


def _lock_lot(db: Session, lot_id: int) -> Lot:
    """
    lot row를 FOR UPDATE로 잠근다.
    """
    lot = db.execute(
        select(Lot)
        .where(Lot.lot_id == lot_id)
        .with_for_update()
    ).scalar_one_or_none()
    if not lot:
        raise HTTPException(status_code=404, detail="LOT not found")
    return lot


def _lock_order_line(db: Session, order_line_id: int) -> OrderLine:
    """
    order_line row를 FOR UPDATE로 잠근다.
    - 트리거가 lot 업데이트 후 order_line을 건드리므로,
      애초에 동일 순서로 락을 잡아 데드락 확률을 낮춘다.
    """
    ol = db.execute(
        select(OrderLine)
        .where(OrderLine.order_line_id == order_line_id)
        .with_for_update()
    ).scalar_one_or_none()
    if not ol or not ol.is_active:
        raise HTTPException(status_code=404, detail="OrderLine not found or inactive")
    return ol


def _lock_entities_in_order(db: Session, lot_step_id: int) -> tuple[OrderLine, Lot, LotStep]:
    """
    ✅ 데드락 방지 핵심:
    항상 order_line -> lot -> lot_step 순으로 락을 잡는다.

    주의:
    - step을 먼저 락 잡으면 step에서 lot_id는 알지만 order_line_id는 lot에서 가져와야 함
    - 그래서 2단계 방식으로 한다:
      1) step을 읽어오되, 바로 락을 잡지 않고 lot_id만 확보
      2) lot를 락 잡고(order_line_id 확보)
      3) order_line 락
      4) 마지막으로 step 락
    """
    # 1) step의 lot_id만 확보 (락 없이)
    tmp = db.get(LotStep, lot_step_id)
    if not tmp:
        raise HTTPException(status_code=404, detail="LotStep not found")
    lot_id = tmp.lot_id

    # 2) lot 락 (order_line_id 확보)
    lot = _lock_lot(db, lot_id)

    # 3) order_line 락 (락 순서 고정)
    ol = _lock_order_line(db, lot.order_line_id)

    # 4) step 락 (마지막)
    step = _lock_lot_step(db, lot_step_id)

    # 방어: step이 다른 lot로 바뀌는 등의 이상 케이스 차단
    if step.lot_id != lot.lot_id:
        raise HTTPException(status_code=409, detail="LotStep/LOT mismatch")

    return ol, lot, step


def _get_prev_step(db: Session, lot_id: int, step_seq: int) -> LotStep | None:
    """
    ✅ step_seq가 10,20,...처럼 점프할 수 있으니
    '바로 이전 번호(step_seq-1)'가 아니라,
    현재보다 작은 것 중 가장 큰 step_seq를 prev로 본다.
    """
    if step_seq <= 0:
        return None

    return db.execute(
        select(LotStep)
        .where(LotStep.lot_id == lot_id, LotStep.step_seq < step_seq)
        .order_by(LotStep.step_seq.desc())
        .limit(1)
    ).scalar_one_or_none()


# ---------------------------
# APIs
# ---------------------------

@router.post("/{lot_step_id}/start", response_model=LotStepOut, status_code=http_status.HTTP_200_OK)
def start_step(lot_step_id: int, db: Session = Depends(get_db)):
    # ✅ 락 순서 고정: order_line -> lot -> lot_step
    ol, lot, step = _lock_entities_in_order(db, lot_step_id)

    # 상태 검증
    if step.status != "WAITING":
        raise HTTPException(status_code=409, detail="Only WAITING step can be started")

    # 이전 공정 완료 확인(순차 진행)
    prev = _get_prev_step(db, step.lot_id, step.step_seq)
    if prev and prev.status != "DONE":
        raise HTTPException(status_code=409, detail="Previous step must be DONE before starting this step")

    # 상태 변경
    step.status = "IN_PROGRESS"
    if step.started_at is None:
        step.started_at = datetime.now(timezone.utc)
     # ✅ LOT 상태는 첫 공정 시작 시점에만 WAITING -> IN_PROGRESS
    if lot.status == "WAITING":
        lot.status = "IN_PROGRESS"
    try:
        db.flush()
        db.commit()
        db.refresh(step)
        return LotStepOut.model_validate(step, from_attributes=True)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Another step is already IN_PROGRESS for this LOT")


@router.post("/{lot_step_id}/complete", response_model=LotStepOut, status_code=http_status.HTTP_200_OK)
def complete_step(lot_step_id: int, db: Session = Depends(get_db)):
    # ✅ 락 순서 고정: order_line -> lot -> lot_step
    ol, lot, step = _lock_entities_in_order(db, lot_step_id)

    if step.status != "IN_PROGRESS":
        raise HTTPException(status_code=409, detail="Only IN_PROGRESS step can be completed")

    step.status = "DONE"
    step.ended_at = datetime.now(timezone.utc)

    # ✅ LOT 상태는 여기서 재계산하지 않음
    # - 중간 공정 완료 후에도 LOT는 계속 IN_PROGRESS 유지
    # - 마지막 DONE 전이는 inspection_result_service 에서 처리

    db.flush()
    db.commit()
    db.refresh(step)
    return LotStepOut.model_validate(step, from_attributes=True)