from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, or_
from fastapi import Path, Query

from app.db.session import get_db, set_local_statement_timeout
from app.models.partner import Partner
from app.schemas.partner import (
    PartnerCreate,
    PartnerOut,
    PartnerListOut,
    PartnerUpdate,
    PartnerBulkCreateRequest,
    PartnerBulkCreateResult,
    PartnerType,
)
from app.services.bulk.partner_bulk_service import partner_bulk_service

router = APIRouter(prefix="/partners", tags=["Partner"])


@router.post("/bulk", response_model=PartnerBulkCreateResult, status_code=status.HTTP_201_CREATED)
def create_partners_bulk(
    payload: PartnerBulkCreateRequest,
    db: Session = Depends(get_db),
):
    try:
        set_local_statement_timeout(db)
        return partner_bulk_service.create_bulk(db, payload)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="business_no already exists",
        )


@router.post("", response_model=PartnerOut, status_code=status.HTTP_201_CREATED)
def create_partner(
    payload: PartnerCreate,
    db: Session = Depends(get_db),
):
    partner = Partner(
        partner_type=payload.partner_type.value,
        name=payload.name,
        business_no=payload.business_no,
        is_active=payload.is_active,
    )
    try:
        db.add(partner)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="business_no already exists",
        )
    db.refresh(partner)
    return partner


@router.get("/{partner_id}", response_model=PartnerOut)
def get_partner(
    partner_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    partner = (
        db.query(Partner)
        .filter(
            Partner.partner_id == partner_id,
            Partner.is_active == True,
        )
        .first()
    )
    if not partner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Partner not found",
        )
    return partner


@router.get("", response_model=PartnerListOut)
def list_partners(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    q: str | None = Query(None),
    is_active: bool | None = Query(True),
    partner_type: PartnerType | None = Query(None),
    db: Session = Depends(get_db),
):
    base = db.query(Partner)

    if is_active is not None:
        base = base.filter(Partner.is_active == is_active)

    if partner_type is not None:
        base = base.filter(Partner.partner_type == partner_type.value)

    if q:
        like = f"%{q}%"
        base = base.filter(
            or_(
                Partner.name.ilike(like),
                Partner.business_no.ilike(like),
            )
        )

    total = base.with_entities(func.count()).scalar() or 0

    items = (
        base.order_by(Partner.partner_id.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )

    return {"items": items, "total": total, "page": page, "size": size}


@router.patch("/{partner_id}", response_model=PartnerOut)
def update_partner(
    partner_id: int,
    payload: PartnerUpdate,
    db: Session = Depends(get_db),
):
    partner = db.query(Partner).filter(Partner.partner_id == partner_id).first()

    if not partner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner not found")

    if payload.partner_type is not None:
        partner.partner_type = payload.partner_type.value
    if payload.name is not None:
        partner.name = payload.name
    if payload.business_no is not None:
        partner.business_no = payload.business_no
    if payload.is_active is not None:
        partner.is_active = payload.is_active

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="business_no already exists")

    db.refresh(partner)
    return partner


@router.delete("/{partner_id}", response_model=PartnerOut)
def deactivate_partner(
    partner_id: int,
    db: Session = Depends(get_db),
):
    partner = db.query(Partner).filter(Partner.partner_id == partner_id).first()

    if not partner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner not found")

    if partner.is_active:
        partner.is_active = False
        db.commit()
        db.refresh(partner)

    return partner
