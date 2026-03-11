# app/api/v1/order_lines.py
from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db  # 너희 프로젝트의 get_db 경로에 맞춰 수정
from app.models.order_line import OrderLine
from app.models.partner import Partner
from app.models.product import Product
from app.schemas.order_line import (
    OrderLineCreate,
    OrderLineUpdate,
    OrderLineOut,
    OrderLineListOut,
    PageMeta,
    OrderLineStatus,
)
from app.crud.order_line import order_line_crud

from sqlalchemy import update, select, exists, and_
from app.models.lot import Lot
from app.models.lot_step import LotStep

router = APIRouter(prefix="/order-lines", tags=["OrderLine"])


def _ensure_partner_active(db: Session, partner_id: int) -> Partner:
    partner = db.get(Partner, partner_id)
    if not partner or not partner.is_active:
        raise HTTPException(status_code=404, detail="Partner not found or inactive")
    return partner


def _ensure_product_active(db: Session, product_id: int) -> Product:
    product = db.get(Product, product_id)
    if not product or not product.is_active:
        raise HTTPException(status_code=404, detail="Product not found or inactive")
    return product


@router.post("", response_model=OrderLineOut, status_code=http_status.HTTP_201_CREATED)
def create_order_line(payload: OrderLineCreate, db: Session = Depends(get_db)):
    # FK validate
    _ensure_partner_active(db, payload.partner_id)
    product = _ensure_product_active(db, payload.product_id)

    # uom 스냅샷: 입력값을 신뢰하지 않고 product.uom으로 강제(권장)
    data = payload.model_dump()
    data["uom"] = product.uom

    obj = OrderLine(**data)
    # status/is_active/priority는 모델 default 사용(OPEN/true/0)

    try:
        order_line_crud.create(db, obj)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Duplicate order_no+line_no or integrity error")

    # join 표시 필드까지 내려주려면 list_with_search 방식이지만, 단건은 간단히 포함 필드 없이 반환
    # (원하면 여기서 partner/product join해서 partner_name/product_name 넣어줄 수 있음)
    return OrderLineOut.model_validate(obj, from_attributes=True)


@router.get("", response_model=OrderLineListOut)
def list_order_lines(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    q: Optional[str] = Query(None),
    status: Optional[OrderLineStatus] = Query(None),
    is_active: Optional[bool] = Query(True),
    partner_id: Optional[int] = Query(None),
    product_id: Optional[int] = Query(None),
    order_date_from: Optional[date] = Query(None),
    order_date_to: Optional[date] = Query(None),
    due_date_from: Optional[date] = Query(None),
    due_date_to: Optional[date] = Query(None),
):
    items, total = order_line_crud.list_with_search(
        db,
        page=page,
        size=size,
        q=q,
        status=status.value if status else None,
        is_active=is_active,
        partner_id=partner_id,
        product_id=product_id,
        order_date_from=order_date_from,
        order_date_to=order_date_to,
        due_date_from=due_date_from,
        due_date_to=due_date_to,
    )

    return OrderLineListOut(
        items=[OrderLineOut(**x) for x in items],
        meta=PageMeta(page=page, size=size, total=total),
    )


@router.get("/{order_line_id}", response_model=OrderLineOut)
def get_order_line(order_line_id: int, db: Session = Depends(get_db)):
    obj = order_line_crud.get(db, order_line_id)
    if not obj or not obj.is_active:
        raise HTTPException(status_code=404, detail="OrderLine not found")

    # 단건에서도 partner/product 표시 필드 채우고 싶으면 join 1회 수행
    partner = db.get(Partner, obj.partner_id)
    product = db.get(Product, obj.product_id)

    out = OrderLineOut.model_validate(obj, from_attributes=True)
    out.partner_name = partner.name if partner else None
    out.product_code = product.product_code if product else None
    out.product_name = product.product_name if product else None
    return out


@router.patch("/{order_line_id}", response_model=OrderLineOut)
def update_order_line(order_line_id: int, payload: OrderLineUpdate, db: Session = Depends(get_db)):
    obj = order_line_crud.get(db, order_line_id)
    if not obj or not obj.is_active:
        raise HTTPException(status_code=404, detail="OrderLine not found")

    data = payload.model_dump(exclude_unset=True)

    # ✅ CLOSED에서 due_date 변경을 허용하기 위해, 먼저 요청된 due_date를 따로 보관
    requested_due_date = data.get("due_date")

    # 상태 기반 수정 제한
    if obj.status == OrderLineStatus.OPEN.value:
        # OPEN: 기존 정책 그대로 (모든 필드 수정 가능 범위는 data에 들어온 것 기준)
        pass

    elif obj.status == OrderLineStatus.CLOSED.value:
        # ✅ CLOSED: due_date + memo/customer_po만 허용
        allow_keys = {"due_date", "memo", "customer_po"}
        forbidden = set(data.keys()) - allow_keys
        if forbidden:
            raise HTTPException(
                status_code=409,
                detail="CLOSED OrderLine can only modify due_date/memo/customer_po",
            )
        data = {k: v for k, v in data.items() if k in allow_keys}

    else:
        # DONE/CANCELED: memo/customer_po만 허용(기존 정책 유지)
        forbidden_keys = {
            "order_no", "line_no",
            "partner_id", "product_id",
            "order_date", "due_date",
            "order_qty", "uom",
            "priority",
        }
        if any(k in data for k in forbidden_keys):
            raise HTTPException(status_code=409, detail="Only OPEN OrderLine can be modified (except memo/customer_po)")

        allow_keys = {"memo", "customer_po"}
        data = {k: v for k, v in data.items() if k in allow_keys}
    old_due_date = obj.due_date
    # FK validate if changed (OPEN에서만 도달)
    if "partner_id" in data:
        _ensure_partner_active(db, data["partner_id"])
    if "product_id" in data:
        product = _ensure_product_active(db, data["product_id"])
        data["uom"] = product.uom
   
    try:
        order_line_crud.update(db, obj, data)

        # ✅ due_date가 실제로 변경되면 "미시작 LOT만" 동기화
        if requested_due_date is not None and requested_due_date != old_due_date:
            # 주의: 위 update로 obj.due_date가 이미 바뀌었을 수 있으니,
            # rowcount 기준으로 동기화는 "payload 값"으로 수행
            _sync_lot_due_date_for_not_started(db, order_line_id, requested_due_date)

        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Duplicate order_no+line_no or integrity error")

    # 표시 필드 포함해서 반환
    partner = db.get(Partner, obj.partner_id)
    product = db.get(Product, obj.product_id)
    out = OrderLineOut.model_validate(obj, from_attributes=True)
    out.partner_name = partner.name if partner else None
    out.product_code = product.product_code if product else None
    out.product_name = product.product_name if product else None
    return out

@router.delete("/{order_line_id}", response_model=OrderLineOut)
def delete_order_line(order_line_id: int, db: Session = Depends(get_db)):
    obj = order_line_crud.get(db, order_line_id)
    if not obj or not obj.is_active:
        raise HTTPException(status_code=404, detail="OrderLine not found")

    # MVP 안전장치: OPEN일 때만 삭제 허용(권장)
    if obj.status != OrderLineStatus.OPEN.value:
        raise HTTPException(status_code=409, detail="Only OPEN OrderLine can be deleted")

    order_line_crud.soft_delete(db, obj)
    db.commit()

    out = OrderLineOut.model_validate(obj, from_attributes=True)
    return out

def _sync_lot_due_date_for_not_started(db: Session, order_line_id: int, new_due_date: date) -> int:
    """
    OrderLine.due_date 변경 시:
    - 아직 시작 안 한 LOT(= lot_step 중 WAITING 아닌 것이 없음)만 lot.due_date를 동기화
    """
    started_exists = (
        select(LotStep.lot_step_id)
        .where(and_(LotStep.lot_id == Lot.lot_id, LotStep.status != "WAITING"))
        .limit(1)
    )

    stmt = (
        update(Lot)
        .where(Lot.order_line_id == order_line_id)
        .where(~exists(started_exists))
        .values(due_date=new_due_date)
    )

    result = db.execute(stmt)
    return result.rowcount or 0