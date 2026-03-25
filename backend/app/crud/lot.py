# app/crud/lot.py
from __future__ import annotations

from datetime import date
from typing import Optional, Tuple, List, Dict

from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session

from app.models.lot import Lot
from app.models.lot_step import LotStep
from app.models.order_line import OrderLine
from app.models.partner import Partner
from app.models.product import Product


class LotCRUD:
    def get(self, db: Session, lot_id: int) -> Optional[Lot]:
        return db.get(Lot, lot_id)

    def create(self, db: Session, obj: Lot) -> Lot:
        db.add(obj)
        db.flush()
        db.refresh(obj)
        return obj

    def list_with_joins(
        self,
        db: Session,
        *,
        page: int,
        size: int,
        q: Optional[str] = None,
        status: Optional[str] = None,
        order_line_id: Optional[int] = None,
        product_id: Optional[int] = None,
        partner_id: Optional[int] = None,
        due_date_from: Optional[date] = None,
        due_date_to: Optional[date] = None,
        created_date_from: Optional[date] = None,
        created_date_to: Optional[date] = None,
    ) -> Tuple[List[Dict], int]:
        stmt = (
            select(
                Lot,
                OrderLine.order_no.label("order_no"),
                OrderLine.line_no.label("line_no"),
                OrderLine.partner_id.label("partner_id"),
                Partner.name.label("partner_name"),
                Product.product_code.label("product_code"),
                Product.product_name.label("product_name"),
            )
            .join(OrderLine, OrderLine.order_line_id == Lot.order_line_id)
            .join(Partner, Partner.partner_id == OrderLine.partner_id)
            .join(Product, Product.product_id == Lot.product_id)
        )

        conds = []
        if order_line_id:
            conds.append(Lot.order_line_id == order_line_id)
        if product_id:
            conds.append(Lot.product_id == product_id)
        if partner_id:
            conds.append(OrderLine.partner_id == partner_id)

        if status:
            conds.append(Lot.status == status)    

        if due_date_from:
            conds.append(Lot.due_date >= due_date_from)
        if due_date_to:
            conds.append(Lot.due_date <= due_date_to)

        if created_date_from:
            conds.append(Lot.created_date >= created_date_from)
        if created_date_to:
            conds.append(Lot.created_date <= created_date_to)

        if q:
            like = f"%{q}%"
            conds.append(
                or_(
                    Lot.lot_no.ilike(like),
                    OrderLine.order_no.ilike(like),
                    Partner.name.ilike(like),
                    Product.product_name.ilike(like),
                    Product.product_code.ilike(like),
                )
            )

        if conds:
            stmt = stmt.where(*conds)

        count_stmt = (
            select(func.count())
            .select_from(Lot)
            .join(OrderLine, OrderLine.order_line_id == Lot.order_line_id)
            .join(Partner, Partner.partner_id == OrderLine.partner_id)
            .join(Product, Product.product_id == Lot.product_id)
        )
        if conds:
            count_stmt = count_stmt.where(*conds)

        total = db.execute(count_stmt).scalar_one()

        stmt = stmt.order_by(Lot.due_date.asc(), Lot.created_date.asc(), Lot.lot_id.asc())
        stmt = stmt.offset((page - 1) * size).limit(size)

        rows = db.execute(stmt).all()

        items: List[Dict] = []
        for lot, order_no, line_no, ol_partner_id, partner_name, product_code, product_name in rows:
            items.append(
                {
                    "lot_id": lot.lot_id,
                    "lot_no": lot.lot_no,
                    "order_line_id": lot.order_line_id,
                    "product_id": lot.product_id,
                    "parent_lot_id": lot.parent_lot_id,
                    "lot_qty": int(lot.lot_qty),
                    "uom": lot.uom,
                    "created_date": lot.created_date,
                    "due_date": lot.due_date,
                    "status": lot.status,
                    "memo": lot.memo,
                    "created_at": lot.created_at,
                    "updated_at": lot.updated_at,
                    "order_no": order_no,
                    "line_no": line_no,
                    "partner_id": ol_partner_id,
                    "partner_name": partner_name,
                    "product_code": product_code,
                    "product_name": product_name,
                }
            )

        return items, total


lot_crud = LotCRUD()