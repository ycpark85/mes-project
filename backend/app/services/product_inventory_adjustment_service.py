from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.product_inventory import ProductInventory
from app.models.product_inventory_lot import ProductInventoryLot
from app.models.product_inventory_movement import ProductInventoryMovement
from app.schemas.inventory import ProductInventoryAdjustmentIn, ProductInventoryMovementOut


@dataclass(frozen=True)
class ProductInventoryAdjustmentResult:
    product: Product
    movement: ProductInventoryMovement


def adjust_product_inventory_in_session(
    db: Session,
    *,
    product_id: int,
    payload: ProductInventoryAdjustmentIn,
    direction: str,
) -> ProductInventoryAdjustmentResult:
    product = db.get(Product, product_id)
    if not product or not product.is_active:
        raise HTTPException(status_code=404, detail="Product not found")

    normalized_direction = direction.strip().upper()
    if normalized_direction not in {"IN", "OUT"}:
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

    movements: list[ProductInventoryMovement] = []

    if normalized_direction == "IN":
        movements.append(_adjust_inventory_in(db, product_id, payload, inventory))
    else:
        movements.extend(_adjust_inventory_out(db, product_id, payload, inventory))

    for movement in movements:
        db.add(movement)

    db.flush()

    return ProductInventoryAdjustmentResult(product=product, movement=movements[-1])


def build_product_inventory_movement_out(
    *,
    movement: ProductInventoryMovement,
    product: Product,
) -> ProductInventoryMovementOut:
    return ProductInventoryMovementOut(
        inventory_movement_id=movement.inventory_movement_id,
        product_id=movement.product_id,
        product_inventory_lot_id=movement.product_inventory_lot_id,
        stock_lot_no=movement.stock_lot_no,
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


def _adjust_inventory_in(
    db: Session,
    product_id: int,
    payload: ProductInventoryAdjustmentIn,
    inventory: ProductInventory,
) -> ProductInventoryMovement:
    lot_no = (payload.stock_lot_no or "").strip().upper()
    if not lot_no:
        raise HTTPException(status_code=422, detail="재고증가 시 조정 LOT 번호를 입력해야 합니다.")

    inventory_lot = (
        db.execute(
            select(ProductInventoryLot)
            .where(
                ProductInventoryLot.product_id == product_id,
                func.upper(ProductInventoryLot.lot_no) == lot_no,
            )
            .with_for_update()
        )
        .scalar_one_or_none()
    )

    if inventory_lot is None:
        inventory_lot = ProductInventoryLot(
            product_id=product_id,
            lot_no=lot_no,
            current_qty=0,
        )
        db.add(inventory_lot)
        db.flush()

    inventory.current_qty = int(inventory.current_qty or 0) + payload.qty
    inventory_lot.current_qty = int(inventory_lot.current_qty or 0) + payload.qty

    return ProductInventoryMovement(
        product_id=product_id,
        product_inventory_lot_id=inventory_lot.product_inventory_lot_id,
        stock_lot_no=inventory_lot.lot_no,
        movement_type="ADJUST_IN",
        qty=payload.qty,
        balance_after=inventory.current_qty,
        source_type="MANUAL_ADJUST",
        source_id=None,
        memo=payload.memo,
    )


def _adjust_inventory_out(
    db: Session,
    product_id: int,
    payload: ProductInventoryAdjustmentIn,
    inventory: ProductInventory,
) -> list[ProductInventoryMovement]:
    current_qty = int(inventory.current_qty or 0)
    if current_qty < payload.qty:
        raise HTTPException(
            status_code=409,
            detail=f"재고감소 수량이 현재 재고보다 큽니다. 현재고={current_qty}",
        )

    inventory_lots = (
        db.execute(
            select(ProductInventoryLot)
            .where(
                ProductInventoryLot.product_id == product_id,
                ProductInventoryLot.current_qty > 0,
            )
            .order_by(
                ProductInventoryLot.created_at.asc(),
                ProductInventoryLot.product_inventory_lot_id.asc(),
            )
            .with_for_update()
        )
        .scalars()
        .all()
    )

    remaining_qty = payload.qty
    movements: list[ProductInventoryMovement] = []

    for inventory_lot in inventory_lots:
        if remaining_qty <= 0:
            break

        lot_qty = int(inventory_lot.current_qty or 0)
        adjust_qty = min(lot_qty, remaining_qty)
        if adjust_qty <= 0:
            continue

        inventory.current_qty = int(inventory.current_qty or 0) - adjust_qty
        inventory_lot.current_qty = lot_qty - adjust_qty
        remaining_qty -= adjust_qty

        movements.append(
            ProductInventoryMovement(
                product_id=product_id,
                product_inventory_lot_id=inventory_lot.product_inventory_lot_id,
                stock_lot_no=inventory_lot.lot_no,
                movement_type="ADJUST_OUT",
                qty=-adjust_qty,
                balance_after=inventory.current_qty,
                source_type="MANUAL_ADJUST",
                source_id=None,
                memo=payload.memo,
            )
        )

    if remaining_qty > 0:
        raise HTTPException(
            status_code=409,
            detail=(
                "LOT별 재고가 부족하여 재고감소를 처리할 수 없습니다. "
                "재고 정합성 점검 후 보정이 필요합니다."
            ),
        )

    return movements
