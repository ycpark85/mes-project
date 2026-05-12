from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.defect_type import DefectType
from app.schemas.defect_type import (
    DefectTypeCreate,
    DefectTypeUpdate,
    DefectTypeOut,
    DefectTypeListOut,
)
from app.crud.defect_type import defect_type_crud

router = APIRouter(prefix="/defect-types", tags=["DefectType"])


@router.post("", response_model=DefectTypeOut, status_code=status.HTTP_201_CREATED)
def create_defect_type(payload: DefectTypeCreate, db: Session = Depends(get_db)):
    obj = DefectType(
        code=payload.code,
        category1_name=payload.category1_name,
        category2_name=payload.category2_name,
        memo=payload.memo,
        is_active=payload.is_active,
    )
    return defect_type_crud.create(db, obj)


@router.get("/{defect_type_id}", response_model=DefectTypeOut)
def get_defect_type(
    defect_type_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    return defect_type_crud.get_or_404(db, defect_type_id, active_only=True)


@router.get("", response_model=DefectTypeListOut)
def list_defect_types(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    q: str | None = Query(None),
    is_active: bool | None = Query(True),
    db: Session = Depends(get_db),
):
    items, total = defect_type_crud.list_paged(db, page=page, size=size, q=q, is_active=is_active)
    return {"items": items, "total": total, "page": page, "size": size}


@router.patch("/{defect_type_id}", response_model=DefectTypeOut)
def update_defect_type(
    defect_type_id: int = Path(..., ge=1),
    payload: DefectTypeUpdate = None,
    db: Session = Depends(get_db),
):
    obj = defect_type_crud.get_or_404(db, defect_type_id, active_only=False)

    if payload.category1_name is not None:
        obj.category1_name = payload.category1_name

    if payload.category2_name is not None:
        obj.category2_name = payload.category2_name

    if payload.memo is not None:
        obj.memo = payload.memo

    if payload.is_active is not None:
        obj.is_active = payload.is_active

    return defect_type_crud.commit(db, obj)


@router.delete("/{defect_type_id}", response_model=DefectTypeOut)
def delete_defect_type(
    defect_type_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    return defect_type_crud.soft_delete(db, defect_type_id)