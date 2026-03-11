from fastapi import APIRouter, Depends, Query, Path, status, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from app.db.session import get_db
from app.models.product import Product
from app.models.drawing import Drawing
from app.models.routing_template import RoutingTemplate
from app.schemas.product import ProductCreate, ProductUpdate, ProductOut, ProductListOut
from app.crud.product import product_crud

router = APIRouter(prefix="/products", tags=["Product"])


def _ensure_drawing_exists(db: Session, drawing_id: int):
    if not db.query(Drawing.drawing_id).filter(Drawing.drawing_id == drawing_id, Drawing.is_active == True).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="drawing_id not found")


def _ensure_routing_template_exists(db: Session, routing_template_id: int):
    if not db.query(RoutingTemplate.routing_template_id).filter(
        RoutingTemplate.routing_template_id == routing_template_id,
        RoutingTemplate.is_active == True,
    ).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="routing_template_id not found")


def _ensure_fk_exists(db: Session, drawing_id: int, routing_template_id: int):
    _ensure_drawing_exists(db, drawing_id)
    _ensure_routing_template_exists(db, routing_template_id)


@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate, db: Session = Depends(get_db)):
    _ensure_fk_exists(db, payload.drawing_id, payload.routing_template_id)

    obj = Product(
        product_code=payload.product_code,
        product_name=payload.product_name,
        uom=payload.uom,
        drawing_id=payload.drawing_id,
        routing_template_id=payload.routing_template_id,
        panel_width_mm=payload.panel_width_mm,
        panel_length_mm=payload.panel_length_mm,
        product_spec=payload.product_spec,
        cut_qty_per_panel=payload.cut_qty_per_panel,
        is_active=payload.is_active,
        memo=payload.memo,
    )

    try:
        return product_crud.create(db, obj)
    except IntegrityError:
        db.rollback()

        # 1) product_code 중복
        if db.query(Product.product_id).filter(Product.product_code == payload.product_code).first():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="product_code already exists")

        # 2) drawing_id 1:1 중복
        if db.query(Product.product_id).filter(Product.drawing_id == payload.drawing_id).first():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="drawing_id already assigned to another product")

        # 그 외
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="conflict")


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: int = Path(..., ge=1), db: Session = Depends(get_db)):
    return product_crud.get_or_404(db, product_id, active_only=True)


@router.get("", response_model=ProductListOut)
def list_products(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    q: str | None = Query(None),
    is_active: bool | None = Query(True),
    db: Session = Depends(get_db),
):
    items, total = product_crud.list_paged(db, page=page, size=size, q=q, is_active=is_active)
    return {"items": items, "total": total, "page": page, "size": size}


@router.patch("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: int = Path(..., ge=1),
    payload: ProductUpdate = None,
    db: Session = Depends(get_db),
):
    obj = product_crud.get_or_404(db, product_id, active_only=False)

    # FK 변경이 들어오는 경우만 검증
    new_drawing_id = payload.drawing_id if payload.drawing_id is not None else obj.drawing_id
    new_rt_id = payload.routing_template_id if payload.routing_template_id is not None else obj.routing_template_id
    if payload.drawing_id is not None or payload.routing_template_id is not None:
        _ensure_fk_exists(db, new_drawing_id, new_rt_id)

    # 필드 반영
    if payload.product_name is not None:
        obj.product_name = payload.product_name
    if payload.uom is not None:
        obj.uom = payload.uom
    if payload.drawing_id is not None:
        obj.drawing_id = payload.drawing_id
    if payload.routing_template_id is not None:
        obj.routing_template_id = payload.routing_template_id

    if payload.panel_width_mm is not None:
        obj.panel_width_mm = payload.panel_width_mm
    if payload.panel_length_mm is not None:
        obj.panel_length_mm = payload.panel_length_mm
    if payload.product_spec is not None:
        obj.product_spec = payload.product_spec
    if payload.cut_qty_per_panel is not None:
        obj.cut_qty_per_panel = payload.cut_qty_per_panel

    if payload.is_active is not None:
        obj.is_active = payload.is_active
    if payload.memo is not None:
        obj.memo = payload.memo

    try:
        return product_crud.commit(db, obj)
    except IntegrityError:
        db.rollback()

        # drawing_id 1:1 위반 체크 (본인 제외)
        if payload.drawing_id is not None:
            exists = (
                db.query(Product.product_id)
                .filter(Product.drawing_id == payload.drawing_id, Product.product_id != obj.product_id)
                .first()
            )
            if exists:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="drawing_id already assigned to another product",
                )

        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="conflict")


@router.delete("/{product_id}", response_model=ProductOut)
def delete_product(product_id: int = Path(..., ge=1), db: Session = Depends(get_db)):
    # soft delete
    return product_crud.soft_delete(db, product_id)