from __future__ import annotations

from datetime import date
from typing import Optional, Tuple, List

from sqlalchemy import or_, select, func
from sqlalchemy.orm import Session

from app.models.order_line import OrderLine
from app.models.partner import Partner
from app.models.product import Product
from app.models.lot import Lot
from app.models.product_inventory import ProductInventory
from app.services.ship_qty_policy import calculate_ship_qty
from app.models.product_inventory_movement import ProductInventoryMovement

class OrderLineCRUD:
    def get(self, db: Session, order_line_id: int) -> Optional[OrderLine]:
        return db.get(OrderLine, order_line_id)

    def create(self, db: Session, obj_in: OrderLine) -> OrderLine:
        db.add(obj_in)
        db.flush()
        db.refresh(obj_in)
        return obj_in

    def soft_delete(self, db: Session, obj: OrderLine) -> OrderLine:
        obj.is_active = False
        db.flush()
        db.refresh(obj)
        return obj

    def update(self, db: Session, obj: OrderLine, data: dict) -> OrderLine:
        for k, v in data.items():
            setattr(obj, k, v)
        db.flush()
        db.refresh(obj)
        return obj

    def list_with_search(
        self,
        db: Session,
        *,
        page: int,
        size: int,
        q: Optional[str] = None,
        status: Optional[str] = None,
        status_group: Optional[str] = None,
        is_active: Optional[bool] = True,
        partner_id: Optional[int] = None,
        product_id: Optional[int] = None,
        order_date_from: Optional[date] = None,
        order_date_to: Optional[date] = None,
        due_date_from: Optional[date] = None,
        due_date_to: Optional[date] = None,
    ) -> Tuple[List[dict], int]:
        lot_agg_sq = (
            select(
                Lot.order_line_id.label("order_line_id"),
                func.count(Lot.lot_id).label("lot_count"),
            )
            .group_by(Lot.order_line_id)
            .subquery()
        )

        stmt = (
            select(
                OrderLine,
                Partner.name.label("partner_name"),
                Product.product_code.label("product_code"),
                Product.product_name.label("product_name"),
                func.coalesce(ProductInventory.current_qty, 0).label("current_qty"),
                func.coalesce(lot_agg_sq.c.lot_count, 0).label("lot_count"),
            )
            .join(Partner, Partner.partner_id == OrderLine.partner_id)
            .join(Product, Product.product_id == OrderLine.product_id)
            .outerjoin(ProductInventory, ProductInventory.product_id == OrderLine.product_id)
            .outerjoin(lot_agg_sq, lot_agg_sq.c.order_line_id == OrderLine.order_line_id)
        )

        conds = []

        if is_active is not None:
            conds.append(OrderLine.is_active == is_active)

        if status_group:
            normalized_group = status_group.strip().upper()

            if normalized_group == "IN_PROGRESS":
                conds.append(OrderLine.status.in_(["OPEN", "CLOSED"]))
            elif normalized_group == "COMPLETED":
                conds.append(OrderLine.status.in_(["DONE", "CANCELED"]))
        elif status:
            conds.append(OrderLine.status == status)

        if partner_id:
            conds.append(OrderLine.partner_id == partner_id)

        if product_id:
            conds.append(OrderLine.product_id == product_id)

        if order_date_from:
            conds.append(OrderLine.order_date >= order_date_from)

        if order_date_to:
            conds.append(OrderLine.order_date <= order_date_to)

        if due_date_from:
            conds.append(OrderLine.due_date >= due_date_from)

        if due_date_to:
            conds.append(OrderLine.due_date <= due_date_to)

        if q:
            like = f"%{q}%"
            conds.append(
                or_(
                    OrderLine.order_no.ilike(like),
                    OrderLine.customer_po.ilike(like),
                    OrderLine.memo.ilike(like),
                    Partner.name.ilike(like),
                    Product.product_name.ilike(like),
                    Product.product_code.ilike(like),
                )
            )

        if conds:
            stmt = stmt.where(*conds)

        count_stmt = (
            select(func.count())
            .select_from(OrderLine)
            .join(Partner, Partner.partner_id == OrderLine.partner_id)
            .join(Product, Product.product_id == OrderLine.product_id)
        )

        if conds:
            count_stmt = count_stmt.where(*conds)

        total = db.execute(count_stmt).scalar_one()

        stmt = stmt.order_by(
            OrderLine.due_date.asc(),
            OrderLine.order_no.asc(),
            OrderLine.line_no.asc(),
        )

        stmt = stmt.offset((page - 1) * size).limit(size)

        rows = db.execute(stmt).all()

        items: List[dict] = []

        for ol, partner_name, product_code, product_name, current_qty, lot_count in rows:
            lot_count_int = int(lot_count or 0)
            available_inventory_qty = int(current_qty or 0)
            order_qty = int(ol.order_qty or 0)

            target_ship_qty = int(calculate_ship_qty(partner_name or "", order_qty) or 0)

            if available_inventory_qty <= 0:
                recommended_mode = "PRODUCTION_FIRST"
            elif available_inventory_qty >= target_ship_qty:
                recommended_mode = "INVENTORY_FIRST"
            else:
                recommended_mode = "HYBRID"

            saved_mode = ol.fulfillment_mode or recommended_mode
            saved_policy = ol.production_policy or "ORDER_ONLY"
            extra_production_qty = int(ol.extra_production_qty or 0)

            if saved_policy == "INVENTORY_ONLY_CLOSE":
                saved_mode = "INVENTORY_FIRST"
                extra_production_qty = 0
                base_planned_production_qty = 0
            elif saved_mode == "PRODUCTION_FIRST":
                base_planned_production_qty = target_ship_qty
            else:
                base_planned_production_qty = max(target_ship_qty - available_inventory_qty, 0)

            if saved_policy != "ALLOW_STOCK_BUILD":
                extra_production_qty = 0

            recommended_production_qty = (
                target_ship_qty
                if recommended_mode == "PRODUCTION_FIRST"
                else max(target_ship_qty - available_inventory_qty, 0)
            )

            planned_production_qty = base_planned_production_qty + extra_production_qty

            if saved_policy == "INVENTORY_ONLY_CLOSE":
                expected_ship_qty = min(available_inventory_qty, target_ship_qty)
            else:
                expected_ship_qty = min(
                    available_inventory_qty + planned_production_qty,
                    target_ship_qty,
                )
            ship_target_qty = int(calculate_ship_qty(partner_name or "", int(ol.order_qty or 0)) or 0)

            already_shipped_qty = int(
                db.execute(
                    select(func.coalesce(func.sum(-ProductInventoryMovement.qty), 0)).where(
                        ProductInventoryMovement.order_line_id == ol.order_line_id,
                        ProductInventoryMovement.movement_type == "SHIP_OUT",
                    )
                ).scalar_one()
                or 0
            )

            remaining_ship_qty = max(ship_target_qty - already_shipped_qty, 0)

            needs_shortage_action = (
                ol.status == "CLOSED"
                and remaining_ship_qty > 0
                and (ol.production_policy or "") != "INVENTORY_ONLY_CLOSE"
                and lot_count_int > 0
            )

            shortage_closed = (
                ol.status == "DONE"
                and remaining_ship_qty > 0
            )    

            expected_short_qty = max(target_ship_qty - expected_ship_qty, 0)

            decision_required = (not bool(ol.decision_made)) and ol.status in {"OPEN", "CLOSED"}

            d = {
                "order_line_id": ol.order_line_id,
                "order_no": ol.order_no,
                "line_no": ol.line_no,
                "partner_id": ol.partner_id,
                "product_id": ol.product_id,
                "order_date": ol.order_date,
                "due_date": ol.due_date,
                "order_qty": ol.order_qty,
                "uom": ol.uom,
                "customer_po": ol.customer_po,
                "memo": ol.memo,
                "status": ol.status,
                "is_active": ol.is_active,
                "priority": ol.priority,
                "created_at": ol.created_at,
                "updated_at": ol.updated_at,
                "partner_name": partner_name,
                "product_code": product_code,
                "product_name": product_name,
                "has_lot": lot_count_int > 0,
                "lot_count": lot_count_int,
                "fulfillment_mode": saved_mode,
                "production_policy": saved_policy,
                "extra_production_qty": extra_production_qty,
                "decision_made": bool(ol.decision_made),
                "decision_made_at": ol.decision_made_at,
                "decision_made_by": ol.decision_made_by,
                "available_inventory_qty": available_inventory_qty,
                "target_ship_qty": target_ship_qty,
                "recommended_fulfillment_mode": recommended_mode,
                "recommended_production_qty": recommended_production_qty,
                "planned_production_qty": planned_production_qty,
                "decision_required": decision_required,
                "expected_ship_qty": expected_ship_qty,
                "expected_short_qty": expected_short_qty,
                "ship_target_qty": ship_target_qty,
                "already_shipped_qty": already_shipped_qty,
                "remaining_ship_qty": remaining_ship_qty,
                "needs_shortage_action": needs_shortage_action,
                "shortage_closed": shortage_closed,
            }
            items.append(d)

        return items, total


order_line_crud = OrderLineCRUD()