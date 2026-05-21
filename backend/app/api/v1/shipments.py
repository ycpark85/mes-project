from __future__ import annotations

from datetime import date, datetime, time, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.lot import Lot
from app.models.order_line import OrderLine
from app.models.partner import Partner
from app.models.product import Product
from app.models.product_inventory import ProductInventory
from app.models.product_inventory_movement import ProductInventoryMovement
from app.models.shipment_line import ShipmentLine
from app.schemas.shipment import (
    ShipmentConfirmRequest,
    ShipmentConfirmResult,
    ShipmentLineListOut,
    ShipmentLineOut,
)
from app.services.ship_qty_policy import calculate_ship_qty


router = APIRouter(prefix="/shipments", tags=["Shipments"])


def _get_ship_target_qty(db: Session, order_line: OrderLine) -> int:
    partner = db.get(Partner, order_line.partner_id)
    partner_name = partner.name if partner else ""
    return int(calculate_ship_qty(partner_name, int(order_line.order_qty or 0)) or 0)


def _get_already_shipped_qty(db: Session, order_line_id: int) -> int:
    shipped_qty = db.execute(
        select(func.coalesce(func.sum(-ProductInventoryMovement.qty), 0)).where(
            ProductInventoryMovement.order_line_id == order_line_id,
            ProductInventoryMovement.movement_type == "SHIP_OUT",
        )
    ).scalar_one()

    return int(shipped_qty or 0)


def _sync_order_line_status_after_shipment(db: Session, order_line: OrderLine) -> None:
    if order_line.status in {"CANCELED", "DONE"}:
        return

    ship_target_qty = _get_ship_target_qty(db, order_line)
    already_shipped_qty = _get_already_shipped_qty(db, order_line.order_line_id)

    if already_shipped_qty >= ship_target_qty:
        order_line.status = "DONE"


@router.get("", response_model=ShipmentLineListOut)
def list_shipments(
    status: str = Query("WAITING"),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    q: Optional[str] = Query(None),
    shipped_from: Optional[date] = Query(None),
    shipped_to: Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    normalized_status = status.strip().upper()

    if normalized_status not in {"WAITING", "DONE", "CANCELED"}:
        raise HTTPException(status_code=422, detail="status must be WAITING, DONE, or CANCELED")

    base = (
        select(
            ShipmentLine,
            OrderLine.order_no.label("order_no"),
            Partner.name.label("partner_name"),
            Product.product_code.label("product_code"),
            Product.product_name.label("product_name"),
            Lot.lot_no.label("lot_no"),
        )
        .select_from(ShipmentLine)
        .join(OrderLine, OrderLine.order_line_id == ShipmentLine.order_line_id)
        .join(Partner, Partner.partner_id == OrderLine.partner_id)
        .join(Product, Product.product_id == ShipmentLine.product_id)
        .outerjoin(Lot, Lot.lot_id == ShipmentLine.lot_id)
        .where(ShipmentLine.status == normalized_status)
    )

    count_q = (
        select(func.count())
        .select_from(ShipmentLine)
        .join(OrderLine, OrderLine.order_line_id == ShipmentLine.order_line_id)
        .join(Partner, Partner.partner_id == OrderLine.partner_id)
        .join(Product, Product.product_id == ShipmentLine.product_id)
        .outerjoin(Lot, Lot.lot_id == ShipmentLine.lot_id)
        .where(ShipmentLine.status == normalized_status)
    )

    if q:
        keyword = f"%{q.strip()}%"
        search_cond = or_(
            OrderLine.order_no.ilike(keyword),
            Partner.name.ilike(keyword),
            Product.product_code.ilike(keyword),
            Product.product_name.ilike(keyword),
            Lot.lot_no.ilike(keyword),
        )
        base = base.where(search_cond)
        count_q = count_q.where(search_cond)
        
    if normalized_status == "DONE":
        if shipped_from is not None:
            shipped_from_dt = datetime.combine(shipped_from, time.min).replace(tzinfo=timezone.utc)
            base = base.where(ShipmentLine.shipped_at >= shipped_from_dt)
            count_q = count_q.where(ShipmentLine.shipped_at >= shipped_from_dt)

        if shipped_to is not None:
            shipped_to_dt = datetime.combine(shipped_to, time.max).replace(tzinfo=timezone.utc)
            base = base.where(ShipmentLine.shipped_at <= shipped_to_dt)
            count_q = count_q.where(ShipmentLine.shipped_at <= shipped_to_dt)
    total = int(db.execute(count_q).scalar_one() or 0)

    rows = (
        db.execute(
            base.order_by(
                ShipmentLine.created_at.desc(),
                ShipmentLine.shipment_line_id.desc(),
            )
            .limit(size)
            .offset((page - 1) * size)
        )
        .all()
    )

    items: list[ShipmentLineOut] = []

    for shipment_line, order_no, partner_name, product_code, product_name, lot_no in rows:
        order_line = db.get(OrderLine, shipment_line.order_line_id)

        ship_target_qty = 0
        already_shipped_qty = 0
        remaining_ship_qty = 0

        if order_line is not None:
            ship_target_qty = _get_ship_target_qty(db, order_line)
            already_shipped_qty = _get_already_shipped_qty(db, order_line.order_line_id)
            remaining_ship_qty = max(ship_target_qty - already_shipped_qty, 0)
        
        current_stock_qty = int(
            db.execute(
                select(func.coalesce(ProductInventory.current_qty, 0)).where(
                    ProductInventory.product_id == shipment_line.product_id
                )
            ).scalar_one()
            or 0
        )

        if normalized_status == "WAITING":
            stock_after_ship_qty = max(current_stock_qty - int(shipment_line.ship_qty or 0), 0)
        else:
            stock_after_ship_qty = current_stock_qty    

        items.append(
            ShipmentLineOut(
                shipment_line_id=shipment_line.shipment_line_id,
                order_line_id=shipment_line.order_line_id,
                order_no=order_no,
                partner_name=partner_name,
                product_id=shipment_line.product_id,
                product_code=product_code,
                product_name=product_name,
                lot_id=shipment_line.lot_id,
                lot_no=lot_no,
                inspection_result_id=shipment_line.inspection_result_id,
                source_type=shipment_line.source_type,
                status=shipment_line.status,
                ship_qty=shipment_line.ship_qty,
                shipped_qty=shipment_line.shipped_qty,
                ship_target_qty=ship_target_qty,
                already_shipped_qty=already_shipped_qty,
                remaining_ship_qty=remaining_ship_qty,
                current_stock_qty=current_stock_qty,
                stock_after_ship_qty=stock_after_ship_qty,
                memo=shipment_line.memo,
                created_at=shipment_line.created_at,
                shipped_at=shipment_line.shipped_at,
            )
        )

    return ShipmentLineListOut(
        items=items,
        total=total,
        page=page,
        size=size,
    )


@router.post("/confirm", response_model=ShipmentConfirmResult)
def confirm_shipments(
    payload: ShipmentConfirmRequest,
    db: Session = Depends(get_db),
):
    target_ids = sorted(set(payload.shipment_line_ids))

    lines = (
        db.execute(
            select(ShipmentLine)
            .where(
                ShipmentLine.shipment_line_id.in_(target_ids),
                ShipmentLine.status == "WAITING",
            )
            .with_for_update()
        )
        .scalars()
        .all()
    )

    if len(lines) != len(target_ids):
        raise HTTPException(status_code=409, detail="출하대기 상태가 아닌 항목이 포함되어 있습니다.")

    confirmed_ids: list[int] = []
    affected_order_line_ids: set[int] = set()

    try:
        for line in lines:
            ship_qty = int(line.ship_qty or 0)

            if ship_qty <= 0:
                raise HTTPException(status_code=422, detail="출하수량이 0인 항목은 출하할 수 없습니다.")

            inventory = (
                db.execute(
                    select(ProductInventory)
                    .where(ProductInventory.product_id == line.product_id)
                    .with_for_update()
                )
                .scalar_one_or_none()
            )

            if inventory is None:
                inventory = ProductInventory(
                    product_id=line.product_id,
                    current_qty=0,
                )
                db.add(inventory)
                db.flush()

            if int(inventory.current_qty or 0) < ship_qty:
                raise HTTPException(
                    status_code=409,
                    detail=f"재고가 부족합니다. shipment_line_id={line.shipment_line_id}",
                )

            inventory.current_qty -= ship_qty

            movement = ProductInventoryMovement(
                product_id=line.product_id,
                movement_type="SHIP_OUT",
                qty=-ship_qty,
                balance_after=inventory.current_qty,
                source_type="SHIPMENT_LINE",
                source_id=line.shipment_line_id,
                order_line_id=line.order_line_id,
                inspection_result_id=line.inspection_result_id,
                memo=f"출하관리 출하확정 / shipment_line_id={line.shipment_line_id}",
            )
            db.add(movement)

            line.shipped_qty = ship_qty
            line.status = "DONE"
            line.shipped_at = datetime.now(timezone.utc)

            confirmed_ids.append(line.shipment_line_id)
            affected_order_line_ids.add(line.order_line_id)

        for order_line_id in affected_order_line_ids:
            order_line = (
                db.execute(
                    select(OrderLine)
                    .where(OrderLine.order_line_id == order_line_id)
                    .with_for_update()
                )
                .scalar_one_or_none()
            )

            if order_line is not None:
                _sync_order_line_status_after_shipment(db, order_line)

        db.commit()

        return ShipmentConfirmResult(
            confirmed_count=len(confirmed_ids),
            confirmed_shipment_line_ids=confirmed_ids,
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise