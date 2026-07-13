from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.product_inventory import ProductInventory
from app.models.product_inventory_lot import ProductInventoryLot
from app.models.product_inventory_movement import ProductInventoryMovement
from app.schemas.inventory import (
    InitialInventoryBulkErrorOut,
    InitialInventoryBulkIn,
    InitialInventoryBulkResultOut,
)


@dataclass(frozen=True)
class _NormalizedInitialInventoryItem:
    row_number: int
    product_code: str
    lot_no: str
    initial_qty: int
    memo: str | None


def upload_initial_inventory_bulk_in_session(
    db: Session,
    payload: InitialInventoryBulkIn,
) -> InitialInventoryBulkResultOut:
    errors: list[InitialInventoryBulkErrorOut] = []
    normalized_items = _normalize_initial_inventory_items(payload, errors)

    product_codes = [item.product_code for item in normalized_items]
    products = _load_active_products(db, product_codes)
    product_map = {product.product_code.upper(): product for product in products}
    product_ids = [product.product_id for product in products]

    movement_product_ids = _load_product_ids_with_movements(db, product_ids)
    inventory_map = _load_inventory_map(db, product_ids)
    inventory_lot_map = _load_inventory_lot_map(db, product_ids, [item.lot_no for item in normalized_items])

    success_count = 0
    skipped_count = 0

    for item in normalized_items:
        product = product_map.get(item.product_code)

        if product is None:
            errors.append(
                InitialInventoryBulkErrorOut(
                    row_number=item.row_number,
                    product_code=item.product_code,
                    lot_no=item.lot_no,
                    message="존재하지 않거나 미사용 처리된 품목코드입니다.",
                )
            )
            continue

        if product.product_id in movement_product_ids:
            errors.append(
                InitialInventoryBulkErrorOut(
                    row_number=item.row_number,
                    product_code=item.product_code,
                    lot_no=item.lot_no,
                    message="이미 재고 이력이 있는 품목입니다. 기초재고 등록이 불가능합니다.",
                )
            )
            continue

        if item.initial_qty == 0:
            skipped_count += 1
            continue

        inventory = inventory_map.get(product.product_id)

        if inventory is None:
            inventory = ProductInventory(product_id=product.product_id, current_qty=0)
            db.add(inventory)
            db.flush()
            inventory_map[product.product_id] = inventory

        inventory_lot_key = (product.product_id, item.lot_no)
        inventory_lot = inventory_lot_map.get(inventory_lot_key)

        if inventory_lot is not None and int(inventory_lot.current_qty or 0) != 0:
            errors.append(
                InitialInventoryBulkErrorOut(
                    row_number=item.row_number,
                    product_code=item.product_code,
                    lot_no=item.lot_no,
                    message="이미 재고가 있는 LOT입니다. 기초재고 등록이 불가능합니다.",
                )
            )
            continue

        if inventory_lot is None:
            inventory_lot = ProductInventoryLot(
                product_id=product.product_id,
                lot_no=item.lot_no,
                current_qty=0,
            )
            db.add(inventory_lot)
            db.flush()
            inventory_lot_map[inventory_lot_key] = inventory_lot

        inventory.current_qty = int(inventory.current_qty or 0) + item.initial_qty
        inventory_lot.current_qty = item.initial_qty

        db.add(
            ProductInventoryMovement(
                product_id=product.product_id,
                product_inventory_lot_id=inventory_lot.product_inventory_lot_id,
                stock_lot_no=item.lot_no,
                movement_type="INITIAL_STOCK",
                qty=item.initial_qty,
                balance_after=inventory.current_qty,
                source_type="INITIAL_STOCK_BULK",
                source_id=None,
                memo=item.memo or "기초재고 등록",
            )
        )

        success_count += 1

    db.flush()

    return InitialInventoryBulkResultOut(
        total_count=len(payload.items),
        success_count=success_count,
        skipped_count=skipped_count,
        failure_count=len(errors),
        errors=errors,
    )


def _normalize_initial_inventory_items(
    payload: InitialInventoryBulkIn,
    errors: list[InitialInventoryBulkErrorOut],
) -> list[_NormalizedInitialInventoryItem]:
    normalized_items: list[_NormalizedInitialInventoryItem] = []
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
            _NormalizedInitialInventoryItem(
                row_number=item.row_number,
                product_code=product_code,
                lot_no=lot_no,
                initial_qty=int(item.initial_qty or 0),
                memo=item.memo.strip() if item.memo else None,
            )
        )

    return normalized_items


def _load_active_products(db: Session, product_codes: list[str]) -> list[Product]:
    if not product_codes:
        return []

    return (
        db.execute(
            select(Product).where(
                Product.product_code.in_(product_codes),
                Product.is_active.is_(True),
            )
        )
        .scalars()
        .all()
    )


def _load_product_ids_with_movements(db: Session, product_ids: list[int]) -> set[int]:
    if not product_ids:
        return set()

    return set(
        db.execute(
            select(ProductInventoryMovement.product_id).where(
                ProductInventoryMovement.product_id.in_(product_ids)
            )
        )
        .scalars()
        .all()
    )


def _load_inventory_map(db: Session, product_ids: list[int]) -> dict[int, ProductInventory]:
    if not product_ids:
        return {}

    inventories = (
        db.execute(
            select(ProductInventory)
            .where(ProductInventory.product_id.in_(product_ids))
            .with_for_update()
        )
        .scalars()
        .all()
    )
    return {inventory.product_id: inventory for inventory in inventories}


def _load_inventory_lot_map(
    db: Session,
    product_ids: list[int],
    lot_nos: list[str],
) -> dict[tuple[int, str], ProductInventoryLot]:
    if not product_ids or not lot_nos:
        return {}

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
    return {(inventory_lot.product_id, inventory_lot.lot_no.upper()): inventory_lot for inventory_lot in inventory_lots}
