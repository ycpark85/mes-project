from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.partner import Partner
from app.schemas.partner import PartnerCreate, PartnerUpdate, PartnerOut, PartnerListOut
from app.crud.partner import partner_crud

router = APIRouter(prefix="/partners", tags=["Partner"])


@router.post("", response_model=PartnerOut, status_code=status.HTTP_201_CREATED)
def create_partner(payload: PartnerCreate, db: Session = Depends(get_db)):
    obj = Partner(
        partner_type=payload.partner_type.value,
        name=payload.name,
        business_no=payload.business_no,
        is_active=payload.is_active,
    )
    return partner_crud.create(db, obj)


@router.get("/{partner_id}", response_model=PartnerOut)
def get_partner(
    partner_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    return partner_crud.get_or_404(db, partner_id, active_only=True)


@router.get("", response_model=PartnerListOut)
def list_partners(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    q: str | None = Query(None),
    is_active: bool | None = Query(True),  # 기본 활성만
    db: Session = Depends(get_db),
):
    items, total = partner_crud.list_paged(db, page=page, size=size, q=q, is_active=is_active)
    return {"items": items, "total": total, "page": page, "size": size}


@router.patch("/{partner_id}", response_model=PartnerOut)
def update_partner(
    partner_id: int = Path(..., ge=1),
    payload: PartnerUpdate = None,
    db: Session = Depends(get_db),
):
    obj = partner_crud.get_or_404(db, partner_id, active_only=False)

    # 부분 업데이트
    if payload.partner_type is not None:
        obj.partner_type = payload.partner_type.value
    if payload.name is not None:
        obj.name = payload.name
    if payload.business_no is not None:
        obj.business_no = payload.business_no
    if payload.is_active is not None:
        obj.is_active = payload.is_active

    return partner_crud.commit(db, obj)


@router.delete("/{partner_id}", response_model=PartnerOut)
def delete_partner(
    partner_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    return partner_crud.soft_delete(db, partner_id)