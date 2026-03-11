from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.process import Process
from app.schemas.process import ProcessCreate, ProcessUpdate, ProcessOut, ProcessListOut
from app.crud.process import process_crud

router = APIRouter(prefix="/processes", tags=["Process"])


@router.post("", response_model=ProcessOut, status_code=status.HTTP_201_CREATED)
def create_process(payload: ProcessCreate, db: Session = Depends(get_db)):
    obj = Process(
        process_code=payload.process_code,
        process_name=payload.process_name,
        process_type=payload.process_type.value,
        is_active=payload.is_active,
    )
    return process_crud.create(db, obj)


@router.get("/{process_id}", response_model=ProcessOut)
def get_process(
    process_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    return process_crud.get_or_404(db, process_id, active_only=True)


@router.get("", response_model=ProcessListOut)
def list_processes(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    q: str | None = Query(None),
    is_active: bool | None = Query(True),
    db: Session = Depends(get_db),
):
    items, total = process_crud.list_paged(db, page=page, size=size, q=q, is_active=is_active)
    return {"items": items, "total": total, "page": page, "size": size}


@router.patch("/{process_id}", response_model=ProcessOut)
def update_process(
    process_id: int = Path(..., ge=1),
    payload: ProcessUpdate = None,
    db: Session = Depends(get_db),
):
    obj = process_crud.get_or_404(db, process_id, active_only=False)

    if payload.process_name is not None:
        obj.process_name = payload.process_name
    if payload.process_type is not None:
        obj.process_type = payload.process_type.value
    if payload.is_active is not None:
        obj.is_active = payload.is_active

    return process_crud.commit(db, obj)


@router.delete("/{process_id}", response_model=ProcessOut)
def delete_process(
    process_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    return process_crud.soft_delete(db, process_id)