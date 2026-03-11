from __future__ import annotations

import re
from pathlib import Path
from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Path as FPath,
    status,
    UploadFile,
    File,
    Form,
)
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from app.db.session import get_db
from app.core.config import settings
from app.models.drawing import Drawing
from app.models.drawing_revision import DrawingRevision
from app.schemas.drawing_revision import DrawingRevisionOut, DrawingRevisionListOut

router = APIRouter(prefix="/drawings", tags=["DrawingRevision"])

_filename_safe_re = re.compile(r"[^A-Za-z0-9_.()-]+")


def _safe_filename(name: str) -> str:
    name = name.strip().replace(" ", "_")
    name = _filename_safe_re.sub("_", name)
    return name[:150] if len(name) > 150 else name


def _ext_of(filename: str) -> str:
    return Path(filename).suffix.lower().lstrip(".")


def _ensure_drawing(db: Session, drawing_id: int) -> Drawing:
    drawing = db.query(Drawing).filter(Drawing.drawing_id == drawing_id).first()
    if not drawing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drawing not found")
    return drawing


def _make_store_dir(*, drawing_no: str, rev_no: str) -> Path:
    # {ROOT}/drawings/{drawing_no}/{rev_no}/
    root = Path(settings.DRAWING_STORAGE_ROOT)
    return root / "drawings" / drawing_no / rev_no


def _save_upload_file(*, file: UploadFile, target_dir: Path) -> str:
    """
    returns relative file_uri like:
      drawings/DWG-2026-001/A/20260211_103012_spec.pdf
    """
    ext = _ext_of(file.filename or "")
    if not ext or ext not in settings.DRAWING_ALLOWED_EXT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file extension. allowed={sorted(settings.DRAWING_ALLOWED_EXT)}",
        )

    target_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    original = _safe_filename(file.filename or f"file.{ext}")
    final_name = f"{ts}_{original}"
    abs_path = target_dir / final_name

    max_bytes = settings.DRAWING_MAX_MB * 1024 * 1024
    written = 0

    with abs_path.open("wb") as f:
        while True:
            chunk = file.file.read(1024 * 1024)  # 1MB
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
                    detail=f"File too large. max={settings.DRAWING_MAX_MB}MB",
                )
            f.write(chunk)

    # 상대경로로 저장 (환경 바뀌어도 유지)
    # target_dir = {ROOT}/drawings/{drawing_no}/{rev_no}
    rel_uri = str(Path("drawings") / target_dir.parts[-2] / target_dir.parts[-1] / final_name)
    return rel_uri.replace("\\", "/")


# =========================================================
# 1) 업로드 + 리비전 생성 (+ 기본 최신 자동 지정)
# =========================================================
@router.post(
    "/{drawing_id}/revisions/upload",
    response_model=DrawingRevisionOut,
    status_code=status.HTTP_201_CREATED,
)
def upload_revision(
    drawing_id: int = FPath(..., ge=1),
    rev_no: str = Form(..., max_length=20),
    file: UploadFile = File(...),
    set_as_current: bool = Form(True),  # ✅ 기본 True = 업로드하면 최신 지정
    db: Session = Depends(get_db),
):
    drawing = _ensure_drawing(db, drawing_id)

    store_dir = _make_store_dir(drawing_no=drawing.drawing_no, rev_no=rev_no)
    file_uri = _save_upload_file(file=file, target_dir=store_dir)

    rev = DrawingRevision(
        drawing_id=drawing_id,
        rev_no=rev_no,
        file_uri=file_uri,
    )

    try:
        db.add(rev)
        db.flush()  # revision_id 확보

        if set_as_current:
            drawing.current_revision_id = rev.revision_id

        db.commit()
    except IntegrityError:
        db.rollback()
        # uq(drawing_id, rev_no) 충돌 가능 → 저장 파일 정리
        try:
            (Path(settings.DRAWING_STORAGE_ROOT) / file_uri).unlink(missing_ok=True)
        except Exception:
            pass
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="rev_no already exists in this drawing")

    db.refresh(rev)
    return rev


# =========================================================
# 2) 리비전 이력 리스트 조회(검색/필터 포함)
# =========================================================
@router.get("/{drawing_id}/revisions", response_model=DrawingRevisionListOut)
def list_revisions(
    drawing_id: int = FPath(..., ge=1),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    q: str | None = Query(None),
    rev_no: str | None = Query(None),
    db: Session = Depends(get_db),
):
    _ensure_drawing(db, drawing_id)

    base = db.query(DrawingRevision).filter(DrawingRevision.drawing_id == drawing_id)

    if rev_no:
        base = base.filter(DrawingRevision.rev_no == rev_no)

    if q:
        like = f"%{q}%"
        base = base.filter((DrawingRevision.rev_no.ilike(like)) | (DrawingRevision.file_uri.ilike(like)))

    total = base.with_entities(func.count()).scalar() or 0
    items = (
        base.order_by(DrawingRevision.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )
    return {"items": items, "total": total, "page": page, "size": size}


# =========================================================
# 3) 파일 교체(수정) 허용
#    - rev_no는 그대로 두고 file_uri만 바꿈
#    - 필요시 최신 지정도 가능
# =========================================================
@router.patch("/{drawing_id}/revisions/{revision_id}/file", response_model=DrawingRevisionOut)
def replace_revision_file(
    drawing_id: int = FPath(..., ge=1),
    revision_id: int = FPath(..., ge=1),
    file: UploadFile = File(...),
    set_as_current: bool = Form(False),
    db: Session = Depends(get_db),
):
    drawing = _ensure_drawing(db, drawing_id)

    rev = (
        db.query(DrawingRevision)
        .filter(DrawingRevision.revision_id == revision_id, DrawingRevision.drawing_id == drawing_id)
        .first()
    )
    if not rev:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DrawingRevision not found")

    old_uri = rev.file_uri

    store_dir = _make_store_dir(drawing_no=drawing.drawing_no, rev_no=rev.rev_no)
    new_uri = _save_upload_file(file=file, target_dir=store_dir)

    rev.file_uri = new_uri
    if set_as_current:
        drawing.current_revision_id = rev.revision_id

    db.commit()
    db.refresh(rev)

    # 운영정책: 교체는 "정정" → 기존 파일 제거
    try:
        (Path(settings.DRAWING_STORAGE_ROOT) / old_uri).unlink(missing_ok=True)
    except Exception:
        pass

    return rev


# =========================================================
# 4) 최신 리비전 수동 지정(유지)
# =========================================================
@router.post("/{drawing_id}/current-revision/{revision_id}", response_model=DrawingRevisionOut)
def set_current_revision(
    drawing_id: int = FPath(..., ge=1),
    revision_id: int = FPath(..., ge=1),
    db: Session = Depends(get_db),
):
    drawing = _ensure_drawing(db, drawing_id)

    rev = (
        db.query(DrawingRevision)
        .filter(DrawingRevision.revision_id == revision_id, DrawingRevision.drawing_id == drawing_id)
        .first()
    )
    if not rev:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DrawingRevision not found")

    drawing.current_revision_id = rev.revision_id
    db.commit()
    db.refresh(rev)
    return rev