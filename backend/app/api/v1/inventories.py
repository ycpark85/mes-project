from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.product import Product
from app.models.product_inventory import ProductInventory
from app.models.product_inventory_movement import ProductInventoryMovement
from app.schemas.inventory import (
    ProductInventoryAdjustmentIn,
    ProductInventoryListOut,
    ProductInventoryMovementListOut,
    ProductInventoryMovementOut,
    ProductInventoryOut,
)

router = APIRouter(prefix="/inventories", tags=["Inventory"])


@router.get("", response_model=ProductInventoryListOut)
def list_inventories(
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=200),
    q: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    base = (
        select(
            Product.product_id,
            Product.product_code,
            Product.product_name,
            Product.uom,
            func.coalesce(ProductInventory.current_qty, 0).label("current_qty"),
            ProductInventory.updated_at,
        )
        .select_from(Product)
        .outerjoin(ProductInventory, ProductInventory.product_id == Product.product_id)
        .where(Product.is_active.is_(True))
    )

    count_q = select(func.count()).select_from(Product).where(Product.is_active.is_(True))

    if q:
        keyword = f"%{q.strip()}%"
        base = base.where(
            or_(
                Product.product_code.ilike(keyword),
                Product.product_name.ilike(keyword),
            )
        )
        count_q = count_q.where(
            or_(
                Product.product_code.ilike(keyword),
                Product.product_name.ilike(keyword),
            )
        )

    total = int(db.execute(count_q).scalar_one() or 0)

    rows = (
        db.execute(
            base.order_by(Product.product_code.asc())
            .limit(size)
            .offset((page - 1) * size)
        )
        .mappings()
        .all()
    )

    return ProductInventoryListOut(
        items=[ProductInventoryOut(**dict(row)) for row in rows],
        total=total,
        page=page,
        size=size,
    )


@router.get("/movements", response_model=ProductInventoryMovementListOut)
def list_inventory_movements(
    product_id: Optional[int] = Query(None, ge=1),
    movement_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
):
    base = (
        select(
            ProductInventoryMovement.inventory_movement_id,
            ProductInventoryMovement.product_id,
            Product.product_code,
            Product.product_name,
            ProductInventoryMovement.movement_type,
            ProductInventoryMovement.qty,
            ProductInventoryMovement.balance_after,
            ProductInventoryMovement.source_type,
            ProductInventoryMovement.source_id,
            ProductInventoryMovement.order_line_id,
            ProductInventoryMovement.inspection_schedule_id,
            ProductInventoryMovement.inspection_result_id,
            ProductInventoryMovement.memo,
            ProductInventoryMovement.created_at,
        )
        .select_from(ProductInventoryMovement)
        .join(Product, Product.product_id == ProductInventoryMovement.product_id)
    )

    count_q = select(func.count()).select_from(ProductInventoryMovement)

    if product_id is not None:
        base = base.where(ProductInventoryMovement.product_id == product_id)
        count_q = count_q.where(ProductInventoryMovement.product_id == product_id)

    if movement_type:
        base = base.where(ProductInventoryMovement.movement_type == movement_type)
        count_q = count_q.where(ProductInventoryMovement.movement_type == movement_type)

    total = int(db.execute(count_q).scalar_one() or 0)

    rows = (
    db.execute(
        base.order_by(
            ProductInventoryMovement.created_at.desc(),
            ProductInventoryMovement.inventory_movement_id.desc(),
        )
        .limit(size)
        .offset((page - 1) * size)
    )
    .mappings()
    .all()
    )

    return ProductInventoryMovementListOut(
        items=[ProductInventoryMovementOut(**dict(row)) for row in rows],
        total=total,
        page=page,
        size=size,
    )


@router.post(
    "/{product_id}/adjust",
    response_model=ProductInventoryMovementOut,
    status_code=status.HTTP_201_CREATED,
)
def adjust_inventory(
    product_id: int,
    payload: ProductInventoryAdjustmentIn,
    direction: str = Query(...),
    db: Session = Depends(get_db),
):
    product = db.get(Product, product_id)
    if not product or not product.is_active:
        raise HTTPException(status_code=404, detail="Product not found")

    if direction not in ("IN", "OUT"):
        raise HTTPException(status_code=422, detail="direction must be IN or OUT")

    inventory = (
        db.execute(
            select(ProductInventory)
            .where(ProductInventory.product_id == product_id)
            .with_for_update()
        )
        .scalar_one_or_none()
    )

    if inventory is None:
        inventory = ProductInventory(product_id=product_id, current_qty=0)
        db.add(inventory)
        db.flush()

    signed_qty = payload.qty if direction == "IN" else -payload.qty

    if inventory.current_qty + signed_qty < 0:
        raise HTTPException(status_code=409, detail="Inventory cannot be negative")

    inventory.current_qty += signed_qty

    movement = ProductInventoryMovement(
        product_id=product_id,
        movement_type="ADJUST_IN" if direction == "IN" else "ADJUST_OUT",
        qty=signed_qty,
        balance_after=inventory.current_qty,
        source_type="MANUAL_ADJUST",
        source_id=None,
        memo=payload.memo,
    )

    db.add(movement)
    db.commit()
    db.refresh(movement)

    return ProductInventoryMovementOut(
        inventory_movement_id=movement.inventory_movement_id,
        product_id=movement.product_id,
        product_code=product.product_code,
        product_name=product.product_name,
        movement_type=movement.movement_type,
        qty=movement.qty,
        balance_after=movement.balance_after,
        source_type=movement.source_type,
        source_id=movement.source_id,
        order_line_id=movement.order_line_id,
        inspection_schedule_id=movement.inspection_schedule_id,
        inspection_result_id=movement.inspection_result_id,
        memo=movement.memo,
        created_at=movement.created_at,
    )