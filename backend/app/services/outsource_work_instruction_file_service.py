from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.inspection_schedule import InspectionSchedule
from app.models.outsource_work_group import OutsourceWorkGroup
from app.models.outsource_work_instruction_file import OutsourceWorkInstructionFile


@dataclass(frozen=True)
class PlateDataUploadResult:
    file_name: str
    file_path: str
    content_type: str | None
    file_size: int
    uploaded_at: datetime


@dataclass(frozen=True)
class PlateDataDownloadResult:
    file_path: Path
    media_type: str
    file_name: str


def save_plate_data_file(
    *,
    file_name: str,
    content_type: str | None,
    content: bytes,
    uploaded_at: datetime | None = None,
) -> PlateDataUploadResult:
    uploaded_at = uploaded_at or datetime.now()
    size_bytes = len(content)

    _validate_plate_data_upload(file_name, size_bytes)

    target_path = _build_plate_data_path(file_name, uploaded_at)

    try:
        target_path.write_bytes(content)
    except OSError:
        raise HTTPException(status_code=500, detail="Failed to save uploaded file")

    return PlateDataUploadResult(
        file_name=Path(file_name).name,
        file_path=str(target_path),
        content_type=content_type,
        file_size=size_bytes,
        uploaded_at=uploaded_at,
    )


def get_work_group_plate_data_file(
    db: Session,
    group_id: int,
) -> PlateDataDownloadResult:
    work_group = db.get(OutsourceWorkGroup, group_id)

    if not work_group:
        raise HTTPException(status_code=404, detail="Outsource work group not found")

    if not work_group.is_bundle:
        raise HTTPException(status_code=404, detail="Bundle plate data not found")

    return _get_instruction_plate_data_file(
        db,
        work_group.outsource_work_instruction_id,
    )


def get_inspection_schedule_plate_data_file(
    db: Session,
    inspection_schedule_id: int,
) -> PlateDataDownloadResult:
    schedule = db.get(InspectionSchedule, inspection_schedule_id)

    if not schedule:
        raise HTTPException(status_code=404, detail="Inspection schedule not found")

    if not schedule.outsource_work_group_id:
        raise HTTPException(status_code=404, detail="Plate data file not found")

    work_group = db.get(OutsourceWorkGroup, schedule.outsource_work_group_id)

    if not work_group:
        raise HTTPException(status_code=404, detail="Outsource work group not found")

    return _get_instruction_plate_data_file(
        db,
        work_group.outsource_work_instruction_id,
    )


def _get_instruction_plate_data_file(
    db: Session,
    outsource_work_instruction_id: int,
) -> PlateDataDownloadResult:
    file_row = (
        db.execute(
            select(OutsourceWorkInstructionFile)
            .where(
                OutsourceWorkInstructionFile.outsource_work_instruction_id
                == outsource_work_instruction_id
            )
            .order_by(OutsourceWorkInstructionFile.outsource_work_instruction_file_id.asc())
        )
        .scalars()
        .first()
    )

    if not file_row:
        raise HTTPException(status_code=404, detail="Plate data file not found")

    file_path = Path(file_row.file_path)

    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Plate data file is missing")

    return PlateDataDownloadResult(
        file_path=file_path,
        media_type=file_row.content_type or "application/octet-stream",
        file_name=file_row.file_name,
    )


def _normalize_ext(filename: str) -> str:
    return Path(filename).suffix.lower().strip()


def _sanitize_filename(filename: str) -> str:
    name = Path(filename).name
    return name.replace(" ", "_")


def _validate_plate_data_upload(file_name: str, size_bytes: int) -> None:
    ext = _normalize_ext(file_name)

    if not file_name.strip():
        raise HTTPException(status_code=400, detail="File name is required")

    allowed_ext = settings.PLATE_DATA_ALLOWED_EXT
    if allowed_ext and ext not in allowed_ext:
        raise HTTPException(
            status_code=409,
            detail=f"File extension not allowed: {ext}",
        )

    max_bytes = settings.PLATE_DATA_MAX_MB * 1024 * 1024
    if size_bytes > max_bytes:
        raise HTTPException(
            status_code=409,
            detail=f"File size exceeded: max {settings.PLATE_DATA_MAX_MB}MB",
        )


def _build_plate_data_path(filename: str, uploaded_at: datetime) -> Path:
    safe_name = _sanitize_filename(filename)
    y = f"{uploaded_at.year:04d}"
    m = f"{uploaded_at.month:02d}"
    d = f"{uploaded_at.day:02d}"

    root = Path(settings.PLATE_DATA_STORAGE_ROOT)
    folder = root / "plate_data" / y / m / d
    folder.mkdir(parents=True, exist_ok=True)

    stored_name = f"{uuid4().hex}_{safe_name}"
    return folder / stored_name
