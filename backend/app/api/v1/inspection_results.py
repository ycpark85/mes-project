from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.session import get_db
from app.models.inspection_result import InspectionResult
from app.schemas.inspection_result import (
    InspectionResultGetOut,
    InspectionResultUpsertIn,
    InspectionResultUpsertOut,
)
from app.services.inspection_result_service import upsert_inspection_result


router = APIRouter(prefix="/inspection-schedules", tags=["InspectionResult"])


@router.get("/{inspection_schedule_id}/result", response_model=InspectionResultGetOut)
def get_result(inspection_schedule_id: int, db: Session = Depends(get_db)):
    result = db.execute(
        select(InspectionResult).where(
            InspectionResult.inspection_schedule_id == inspection_schedule_id
        )
    ).scalar_one_or_none()
    return {"result": result}


@router.put("/{inspection_schedule_id}/result", response_model=InspectionResultUpsertOut)
def put_result(
    inspection_schedule_id: int,
    body: InspectionResultUpsertIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        result, sch_status, created_next_id = upsert_inspection_result(
            db,
            inspection_schedule_id,
            good_qty=body.good_qty,
            defect_ship_qty=body.defect_ship_qty,
            defect_qty=body.defect_qty,
            is_partial=body.is_partial,
            next_inspection_date=body.next_inspection_date,
            partial_reason=body.partial_reason,
            defects=body.defects,
            actor=user.username,
        )
        db.commit()
        db.refresh(result)
        return {
            "result": result,
            "schedule_status": sch_status,
            "created_next_schedule_id": created_next_id,
        }
    except Exception:
        db.rollback()
        raise