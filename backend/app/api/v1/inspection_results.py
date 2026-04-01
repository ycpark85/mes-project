from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.inspection_result import InspectionResult
from app.models.inspection_schedule import InspectionSchedule
from app.schemas.inspection_result import (
    DefectAttachmentUploadOut,
    InspectionAccumulatedSummaryOut,
    InspectionResultGetOut,
    InspectionResultUpsertIn,
    InspectionResultUpsertOut,
)
from app.services.inspection_result_service import upsert_inspection_result

router = APIRouter(prefix="/inspection-schedules", tags=["InspectionResult"])

_filename_safe_re = re.compile(r"[^\w.()-]+", re.UNICODE)


def _safe_filename(name: str) -> str:
    name = (name or "").strip().replace(" ", "_")
    name = _filename_safe_re.sub("_", name)
    return name[:150] if len(name) > 150 else name


def _ext_of(filename: str) -> str:
    return Path(filename).suffix.lower().lstrip(".")


def _ensure_schedule(db: Session, inspection_schedule_id: int) -> InspectionSchedule:
    obj = db.execute(
        select(InspectionSchedule).where(
            InspectionSchedule.inspection_schedule_id == inspection_schedule_id
        )
    ).scalar_one_or_none()

    if obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="InspectionSchedule not found",
        )

    return obj


def _make_defect_photo_dir(*, inspection_schedule_id: int) -> Path:
    root = Path(settings.DEFECT_PHOTO_STORAGE_ROOT)
    return root / "defect_photos" / str(inspection_schedule_id)


def _save_defect_photo(
    *,
    file: UploadFile,
    target_dir: Path,
    inspection_schedule_id: int,
) -> tuple[str, str, int, str | None]:
    ext = _ext_of(file.filename or "")
    if not ext or ext not in settings.DEFECT_PHOTO_ALLOWED_EXT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file extension. allowed={sorted(settings.DEFECT_PHOTO_ALLOWED_EXT)}",
        )

    target_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    original = _safe_filename(file.filename or f"file.{ext}")
    final_name = f"{ts}_{original}"
    abs_path = target_dir / final_name

    max_bytes = settings.DEFECT_PHOTO_MAX_MB * 1024 * 1024
    written = 0

    with abs_path.open("wb") as f:
        while True:
            chunk = file.file.read(1024 * 1024)
            if not chunk:
                break

            written += len(chunk)
            if written > max_bytes:
                try:
                    abs_path.unlink(missing_ok=True)
                except Exception:
                    pass

                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File too large. max={settings.DEFECT_PHOTO_MAX_MB}MB",
                )

            f.write(chunk)

    rel_uri = str(Path("defect_photos") / str(inspection_schedule_id) / final_name)
    return rel_uri.replace("\\", "/"), original, written, file.content_type


def _get_accumulated_summary(
    db: Session,
    *,
    inspection_schedule_id: int,
) -> InspectionAccumulatedSummaryOut:
    current_schedule = _ensure_schedule(db, inspection_schedule_id)
    lot_id = current_schedule.lot_id

    row = db.execute(
        select(
            func.coalesce(func.sum(InspectionResult.good_qty), 0),
            func.coalesce(func.sum(InspectionResult.defect_qty), 0),
            func.coalesce(func.sum(InspectionResult.defect_ship_qty), 0),
            func.coalesce(func.sum(InspectionResult.inspected_qty), 0),
        )
        .select_from(InspectionResult)
        .join(
            InspectionSchedule,
            InspectionSchedule.inspection_schedule_id == InspectionResult.inspection_schedule_id,
        )
        .where(
            InspectionSchedule.lot_id == lot_id,
            InspectionSchedule.inspection_schedule_id != inspection_schedule_id,
            InspectionSchedule.status.in_(("PARTIAL_DONE", "DONE")),
        )
    ).one()

    return InspectionAccumulatedSummaryOut(
        good_qty=int(row[0] or 0),
        defect_qty=int(row[1] or 0),
        defect_ship_qty=int(row[2] or 0),
        inspected_qty=int(row[3] or 0),
    )


@router.get("/{inspection_schedule_id}/result", response_model=InspectionResultGetOut)
def get_result(
    inspection_schedule_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    _ = user
    _ensure_schedule(db, inspection_schedule_id)

    result = db.execute(
        select(InspectionResult).where(
            InspectionResult.inspection_schedule_id == inspection_schedule_id
        )
    ).scalar_one_or_none()

    accumulated = _get_accumulated_summary(
        db,
        inspection_schedule_id=inspection_schedule_id,
    )

    return InspectionResultGetOut(
        result=result,
        accumulated=accumulated,
    )


@router.post(
    "/{inspection_schedule_id}/result/photos",
    response_model=DefectAttachmentUploadOut,
    status_code=status.HTTP_201_CREATED,
)
def upload_result_photo(
    inspection_schedule_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    _ = user
    _ensure_schedule(db, inspection_schedule_id)

    target_dir = _make_defect_photo_dir(inspection_schedule_id=inspection_schedule_id)
    file_uri, file_name, file_size, mime_type = _save_defect_photo(
        file=file,
        target_dir=target_dir,
        inspection_schedule_id=inspection_schedule_id,
    )

    return {
        "file_uri": file_uri,
        "file_name": file_name,
        "mime_type": mime_type,
        "file_size": file_size,
    }


@router.put("/{inspection_schedule_id}/result", response_model=InspectionResultUpsertOut)
def put_result(
    inspection_schedule_id: int,
    body: InspectionResultUpsertIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        actor = getattr(user, "username", None) or getattr(user, "login_id", None) or "system"

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
            actor=actor,
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