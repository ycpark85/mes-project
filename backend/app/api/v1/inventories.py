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
    InitialInventoryBulkIn,
    InitialInventoryBulkResultOut,
    InitialInventoryBulkErrorOut,
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

@router.post("/initial-bulk", response_model=InitialInventoryBulkResultOut)
def upload_initial_inventory_bulk(
    payload: InitialInventoryBulkIn,
    db: Session = Depends(get_db),
):
    errors: list[InitialInventoryBulkErrorOut] = []
    normalized_items = []
    seen_codes: dict[str, int] = {}

    for item in payload.items:
        product_code = (item.product_code or "").strip().upper()

        if not product_code:
            errors.append(
                InitialInventoryBulkErrorOut(
                    row_number=item.row_number,
                    product_code=product_code,
                    message="품목코드는 필수입니다.",
                )
            )
            continue

        if product_code in seen_codes:
            errors.append(
                InitialInventoryBulkErrorOut(
                    row_number=item.row_number,
                    product_code=product_code,
                    message=f"엑셀 내 중복 품목코드입니다. 첫 행: {seen_codes[product_code]}",
                )
            )
            continue

        seen_codes[product_code] = item.row_number

        normalized_items.append(
            {
                "row_number": item.row_number,
                "product_code": product_code,
                "initial_qty": int(item.initial_qty or 0),
                "memo": item.memo.strip() if item.memo else None,
            }
        )

    product_codes = [x["product_code"] for x in normalized_items]

    products = (
        db.execute(
            select(Product).where(
                Product.product_code.in_(product_codes),
                Product.is_active.is_(True),
            )
        )
        .scalars()
        .all()
    )

    product_map = {p.product_code.upper(): p for p in products}

    product_ids = [p.product_id for p in products]

    movement_product_ids = set(
        db.execute(
            select(ProductInventoryMovement.product_id).where(
                ProductInventoryMovement.product_id.in_(product_ids)
            )
        )
        .scalars()
        .all()
    )

    inventories = (
        db.execute(
            select(ProductInventory)
            .where(ProductInventory.product_id.in_(product_ids))
            .with_for_update()
        )
        .scalars()
        .all()
    )

    inventory_map = {x.product_id: x for x in inventories}

    success_count = 0
    skipped_count = 0

    for item in normalized_items:
        row_number = item["row_number"]
        product_code = item["product_code"]
        initial_qty = item["initial_qty"]
        memo = item["memo"]

        product = product_map.get(product_code)

        if product is None:
            errors.append(
                InitialInventoryBulkErrorOut(
                    row_number=row_number,
                    product_code=product_code,
                    message="존재하지 않거나 미사용 처리된 품목코드입니다.",
                )
            )
            continue

        if product.product_id in movement_product_ids:
            errors.append(
                InitialInventoryBulkErrorOut(
                    row_number=row_number,
                    product_code=product_code,
                    message="이미 재고 이력이 있는 품목입니다. 기초재고 등록이 불가합니다.",
                )
            )
            continue

        if initial_qty == 0:
            skipped_count += 1
            continue

        inventory = inventory_map.get(product.product_id)

        if inventory is None:
            inventory = ProductInventory(
                product_id=product.product_id,
                current_qty=0,
            )
            db.add(inventory)
            db.flush()
            inventory_map[product.product_id] = inventory

        if int(inventory.current_qty or 0) != 0:
            errors.append(
                InitialInventoryBulkErrorOut(
                    row_number=row_number,
                    product_code=product_code,
                    message="현재고가 0이 아닌 품목입니다. 기초재고 등록이 불가합니다.",
                )
            )
            continue

        inventory.current_qty = initial_qty

        db.add(
            ProductInventoryMovement(
                product_id=product.product_id,
                movement_type="INITIAL_STOCK",
                qty=initial_qty,
                balance_after=initial_qty,
                source_type="INITIAL_STOCK_BULK",
                source_id=None,
                memo=memo or "기초재고 등록",
            )
        )

        success_count += 1

    db.commit()

    return InitialInventoryBulkResultOut(
        total_count=len(payload.items),
        success_count=success_count,
        skipped_count=skipped_count,
        failure_count=len(errors),
        errors=errors,
    )