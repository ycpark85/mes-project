from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.inspection_defect_attachment import InspectionDefectAttachment
from app.models.inspection_schedule import InspectionSchedule

_filename_safe_re = re.compile(r"[^\w.()-]+", re.UNICODE)


@dataclass(frozen=True)
class DefectPhotoUploadResult:
    file_uri: str
    file_name: str
    mime_type: str | None
    file_size: int


@dataclass(frozen=True)
class DefectPhotoDownloadResult:
    file_path: Path
    media_type: str
    file_name: str


def save_defect_photo_upload(
    db: Session,
    inspection_schedule_id: int,
    *,
    file_name: str,
    content_type: str | None,
    file_stream: BinaryIO,
) -> DefectPhotoUploadResult:
    if db.get(InspectionSchedule, inspection_schedule_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="inspection_schedule not found",
        )

    target_dir = _make_defect_photo_dir(inspection_schedule_id=inspection_schedule_id)
    file_uri, original_name, file_size = _save_defect_photo(
        file_name=file_name,
        content_type=content_type,
        file_stream=file_stream,
        target_dir=target_dir,
    )

    return DefectPhotoUploadResult(
        file_uri=file_uri,
        file_name=original_name,
        mime_type=content_type,
        file_size=file_size,
    )


def get_defect_attachment_download(
    db: Session,
    attachment_id: int,
) -> DefectPhotoDownloadResult:
    attachment = db.get(InspectionDefectAttachment, attachment_id)
    if attachment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment not found",
        )

    file_path = _abs_path_from_uri(attachment.file_uri)

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment file not found",
        )

    return DefectPhotoDownloadResult(
        file_path=file_path,
        media_type=attachment.mime_type or _guess_media_type(file_path),
        file_name=attachment.file_name or file_path.name,
    )


def _make_defect_photo_dir(*, inspection_schedule_id: int) -> Path:
    root = Path(settings.DEFECT_PHOTO_STORAGE_ROOT)
    return root / "defect_photos" / str(inspection_schedule_id)


def _save_defect_photo(
    *,
    file_name: str,
    content_type: str | None,
    file_stream: BinaryIO,
    target_dir: Path,
) -> tuple[str, str, int]:
    ext = _ext_of(file_name)
    allowed_exts = _normalize_allowed_exts(settings.DEFECT_PHOTO_ALLOWED_EXT)

    if not ext or ext not in allowed_exts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file extension. allowed={sorted(allowed_exts)}",
        )

    root = Path(settings.DEFECT_PHOTO_STORAGE_ROOT).resolve()
    target_dir = target_dir.resolve()

    try:
        target_dir.relative_to(root)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid storage path",
        )

    target_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    original = _safe_filename(file_name or f"file.{ext}")
    final_name = f"{ts}_{uuid4().hex[:8]}_{original}"
    abs_path = target_dir / final_name

    max_bytes = settings.DEFECT_PHOTO_MAX_MB * 1024 * 1024
    written = 0

    with abs_path.open("wb") as output:
        while True:
            chunk = file_stream.read(1024 * 1024)
            if not chunk:
                break

            written += len(chunk)

            if written > max_bytes:
                _unlink_if_exists(abs_path)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File too large. max={settings.DEFECT_PHOTO_MAX_MB}MB",
                )

            output.write(chunk)

    if written <= 0:
        _unlink_if_exists(abs_path)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file is not allowed",
        )

    rel_uri = str(abs_path.resolve().relative_to(root))
    return rel_uri.replace("\\", "/"), original, written


def _safe_filename(name: str) -> str:
    name = Path((name or "").strip().replace(" ", "_")).name
    name = _filename_safe_re.sub("_", name)
    return name[:150] if len(name) > 150 else name


def _ext_of(filename: str) -> str:
    return Path(filename).suffix.lower().lstrip(".")


def _normalize_allowed_exts(values) -> set[str]:
    return {
        str(value).strip().lower().lstrip(".")
        for value in values
        if str(value).strip()
    }


def _abs_path_from_uri(file_uri: str) -> Path:
    root = Path(settings.DEFECT_PHOTO_STORAGE_ROOT).resolve()
    abs_path = (root / file_uri).resolve()

    try:
        abs_path.relative_to(root)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid attachment path",
        )

    return abs_path


def _guess_media_type(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    if suffix in [".jpg", ".jpeg"]:
        return "image/jpeg"
    if suffix == ".png":
        return "image/png"
    if suffix == ".gif":
        return "image/gif"
    if suffix == ".webp":
        return "image/webp"
    if suffix == ".bmp":
        return "image/bmp"
    return "application/octet-stream"


def _unlink_if_exists(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except Exception:
        pass
