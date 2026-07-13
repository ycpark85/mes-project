from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.product_inventory import ProductInventory
from app.models.product_inventory_lot import ProductInventoryLot
from app.models.product_inventory_movement import ProductInventoryMovement
from app.schemas.inventory import (
    ProductInventoryConsistencyListOut,
    ProductInventoryConsistencyOut,
    ProductInventoryListOut,
    ProductInventoryMovementListOut,
    ProductInventoryMovementOut,
    ProductInventoryOut,
)


def list_product_inventories(
    db: Session,
    *,
    page: int = 1,
    size: int = 100,
    q: str | None = None,
) -> ProductInventoryListOut:
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
        .join(ProductInventory, ProductInventory.product_id == Product.product_id)
        .where(Product.is_active.is_(True))
        .where(ProductInventory.current_qty > 0)
    )

    count_q = (
        select(func.count())
        .select_from(Product)
        .join(ProductInventory, ProductInventory.product_id == Product.product_id)
        .where(Product.is_active.is_(True))
        .where(ProductInventory.current_qty > 0)
    )

    if q:
        keyword = f"%{q.strip()}%"
        search_condition = or_(
            Product.product_code.ilike(keyword),
            Product.product_name.ilike(keyword),
        )
        base = base.where(search_condition)
        count_q = count_q.where(search_condition)

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


def list_product_inventory_movements(
    db: Session,
    *,
    product_id: int | None = None,
    movement_type: str | None = None,
    page: int = 1,
    size: int = 100,
) -> ProductInventoryMovementListOut:
    base = (
        select(
            ProductInventoryMovement.inventory_movement_id,
            ProductInventoryMovement.product_id,
            ProductInventoryMovement.product_inventory_lot_id,
            ProductInventoryMovement.stock_lot_no,
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


def list_product_inventory_consistency(db: Session) -> ProductInventoryConsistencyListOut:
    lot_qty_sq = (
        select(
            ProductInventoryLot.product_id.label("product_id"),
            func.coalesce(func.sum(ProductInventoryLot.current_qty), 0).label("lot_qty"),
        )
        .group_by(ProductInventoryLot.product_id)
        .subquery()
    )

    movement_qty_sq = (
        select(
            ProductInventoryMovement.product_id.label("product_id"),
            func.coalesce(func.sum(ProductInventoryMovement.qty), 0).label("movement_qty"),
        )
        .group_by(ProductInventoryMovement.product_id)
        .subquery()
    )

    current_qty = func.coalesce(ProductInventory.current_qty, 0)
    lot_qty = func.coalesce(lot_qty_sq.c.lot_qty, 0)
    movement_qty = func.coalesce(movement_qty_sq.c.movement_qty, 0)

    rows = (
        db.execute(
            select(
                Product.product_id,
                Product.product_code,
                Product.product_name,
                current_qty.label("current_qty"),
                lot_qty.label("lot_qty"),
                movement_qty.label("movement_qty"),
                (current_qty - lot_qty).label("diff_qty"),
            )
            .select_from(Product)
            .join(ProductInventory, ProductInventory.product_id == Product.product_id)
            .outerjoin(lot_qty_sq, lot_qty_sq.c.product_id == Product.product_id)
            .outerjoin(movement_qty_sq, movement_qty_sq.c.product_id == Product.product_id)
            .where(Product.is_active.is_(True))
            .where((current_qty != lot_qty) | (current_qty != movement_qty))
            .order_by(Product.product_code.asc())
        )
        .mappings()
        .all()
    )

    return ProductInventoryConsistencyListOut(
        items=[ProductInventoryConsistencyOut(**dict(row)) for row in rows],
        total=len(rows),
    )
