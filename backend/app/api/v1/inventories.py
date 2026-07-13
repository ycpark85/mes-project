from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.inventory import (
    InitialInventoryBulkIn,
    InitialInventoryBulkResultOut,
    ProductInventoryAdjustmentIn,
    ProductInventoryConsistencyListOut,
    ProductInventoryListOut,
    ProductInventoryMovementListOut,
    ProductInventoryMovementOut,
)
from app.services.product_inventory_adjustment_service import (
    adjust_product_inventory_in_session,
    build_product_inventory_movement_out,
)
from app.services.product_inventory_initial_bulk_service import upload_initial_inventory_bulk_in_session
from app.services.product_inventory_query import (
    list_product_inventories,
    list_product_inventory_consistency,
    list_product_inventory_movements,
)

router = APIRouter(prefix="/inventories", tags=["Inventory"])


@router.get("", response_model=ProductInventoryListOut)
def list_inventories(
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=200),
    q: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    return list_product_inventories(db, page=page, size=size, q=q)


@router.get("/movements", response_model=ProductInventoryMovementListOut)
def list_inventory_movements(
    product_id: Optional[int] = Query(None, ge=1),
    movement_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return list_product_inventory_movements(
        db,
        product_id=product_id,
        movement_type=movement_type,
        page=page,
        size=size,
    )


@router.get("/consistency", response_model=ProductInventoryConsistencyListOut)
def list_inventory_consistency(db: Session = Depends(get_db)):
    return list_product_inventory_consistency(db)


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
    try:
        result = adjust_product_inventory_in_session(
            db,
            product_id=product_id,
            payload=payload,
            direction=direction,
        )
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise

    db.refresh(result.movement)
    return build_product_inventory_movement_out(movement=result.movement, product=result.product)


@router.post("/initial-bulk", response_model=InitialInventoryBulkResultOut)
def upload_initial_inventory_bulk(
    payload: InitialInventoryBulkIn,
    db: Session = Depends(get_db),
):
    try:
        result = upload_initial_inventory_bulk_in_session(db, payload)
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise
