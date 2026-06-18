from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.product import Product
from app.models.product_inventory import ProductInventory
from app.models.product_inventory_lot import ProductInventoryLot
from app.models.product_inventory_movement import ProductInventoryMovement
from app.schemas.inventory import (
    InitialInventoryBulkErrorOut,
    InitialInventoryBulkIn,
    InitialInventoryBulkResultOut,
    ProductInventoryAdjustmentIn,
    ProductInventoryConsistencyListOut,
    ProductInventoryConsistencyOut,
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


@router.get("/consistency", response_model=ProductInventoryConsistencyListOut)
def list_inventory_consistency(db: Session = Depends(get_db)):
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

    movements: list[ProductInventoryMovement] = []

    if direction == "IN":
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

        movements.append(
            ProductInventoryMovement(
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
        )
    else:
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

    for movement in movements:
        db.add(movement)

    db.commit()
    movement = movements[-1]
    db.refresh(movement)

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


@router.post("/initial-bulk", response_model=InitialInventoryBulkResultOut)
def upload_initial_inventory_bulk(
    payload: InitialInventoryBulkIn,
    db: Session = Depends(get_db),
):
    errors: list[InitialInventoryBulkErrorOut] = []
    normalized_items = []
    seen_keys: dict[tuple[str, str], int] = {}

    for item in payload.items:
        product_code = (item.product_code or "").strip().upper()
        lot_no = (item.lot_no or "").strip().upper()

        if not product_code:
            errors.append(
                InitialInventoryBulkErrorOut(
                    row_number=item.row_number,
                    product_code=product_code,
                    lot_no=lot_no,
                    message="품목코드는 필수입니다.",
                )
            )
            continue

        if not lot_no:
            errors.append(
                InitialInventoryBulkErrorOut(
                    row_number=item.row_number,
                    product_code=product_code,
                    lot_no=lot_no,
                    message="LOT 번호는 필수입니다.",
                )
            )
            continue

        key = (product_code, lot_no)
        if key in seen_keys:
            errors.append(
                InitialInventoryBulkErrorOut(
                    row_number=item.row_number,
                    product_code=product_code,
                    lot_no=lot_no,
                    message=f"엑셀 내 중복 품목/LOT입니다. 첫 행: {seen_keys[key]}",
                )
            )
            continue

        seen_keys[key] = item.row_number
        normalized_items.append(
            {
                "row_number": item.row_number,
                "product_code": product_code,
                "lot_no": lot_no,
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

    lot_nos = [x["lot_no"] for x in normalized_items]
    inventory_lots = (
        db.execute(
            select(ProductInventoryLot)
            .where(
                ProductInventoryLot.product_id.in_(product_ids),
                ProductInventoryLot.lot_no.in_(lot_nos),
            )
            .with_for_update()
        )
        .scalars()
        .all()
    )
    inventory_lot_map = {(x.product_id, x.lot_no.upper()): x for x in inventory_lots}

    success_count = 0
    skipped_count = 0

    for item in normalized_items:
        row_number = item["row_number"]
        product_code = item["product_code"]
        lot_no = item["lot_no"]
        initial_qty = item["initial_qty"]
        memo = item["memo"]

        product = product_map.get(product_code)

        if product is None:
            errors.append(
                InitialInventoryBulkErrorOut(
                    row_number=row_number,
                    product_code=product_code,
                    lot_no=lot_no,
                    message="존재하지 않거나 미사용 처리된 품목코드입니다.",
                )
            )
            continue

        if product.product_id in movement_product_ids:
            errors.append(
                InitialInventoryBulkErrorOut(
                    row_number=row_number,
                    product_code=product_code,
                    lot_no=lot_no,
                    message="이미 재고 이력이 있는 품목입니다. 기초재고 등록이 불가능합니다.",
                )
            )
            continue

        if initial_qty == 0:
            skipped_count += 1
            continue

        inventory = inventory_map.get(product.product_id)

        if inventory is None:
            inventory = ProductInventory(product_id=product.product_id, current_qty=0)
            db.add(inventory)
            db.flush()
            inventory_map[product.product_id] = inventory

        inventory_lot_key = (product.product_id, lot_no)
        inventory_lot = inventory_lot_map.get(inventory_lot_key)

        if inventory_lot is not None and int(inventory_lot.current_qty or 0) != 0:
            errors.append(
                InitialInventoryBulkErrorOut(
                    row_number=row_number,
                    product_code=product_code,
                    lot_no=lot_no,
                    message="이미 재고가 있는 LOT입니다. 기초재고 등록이 불가능합니다.",
                )
            )
            continue

        if inventory_lot is None:
            inventory_lot = ProductInventoryLot(
                product_id=product.product_id,
                lot_no=lot_no,
                current_qty=0,
            )
            db.add(inventory_lot)
            db.flush()
            inventory_lot_map[inventory_lot_key] = inventory_lot

        inventory.current_qty = int(inventory.current_qty or 0) + initial_qty
        inventory_lot.current_qty = initial_qty

        db.add(
            ProductInventoryMovement(
                product_id=product.product_id,
                product_inventory_lot_id=inventory_lot.product_inventory_lot_id,
                stock_lot_no=lot_no,
                movement_type="INITIAL_STOCK",
                qty=initial_qty,
                balance_after=inventory.current_qty,
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
