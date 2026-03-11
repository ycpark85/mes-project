# app/crud/order_line.py
from __future__ import annotations

from datetime import date
from typing import Optional, Tuple, List

from sqlalchemy import or_, select, func
from sqlalchemy.orm import Session

from app.models.order_line import OrderLine
from app.models.partner import Partner
from app.models.product import Product


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
        is_active: Optional[bool] = True,
        partner_id: Optional[int] = None,
        product_id: Optional[int] = None,
        order_date_from: Optional[date] = None,
        order_date_to: Optional[date] = None,
        due_date_from: Optional[date] = None,
        due_date_to: Optional[date] = None,
    ) -> Tuple[List[dict], int]:
        """
        반환:
          - items: dict 리스트(주요 컬럼 + partner_name/product_code/product_name)
          - total: 전체 건수
        """
        # base select with joins for display fields
        stmt = (
            select(
                OrderLine,
                Partner.name.label("partner_name"),
                Product.product_code.label("product_code"),
                Product.product_name.label("product_name"),
            )
            .join(Partner, Partner.partner_id == OrderLine.partner_id)
            .join(Product, Product.product_id == OrderLine.product_id)
        )

        # filters
        conds = []
        if is_active is not None:
            conds.append(OrderLine.is_active == is_active)
        if status:
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

        # count
        count_stmt = (
            select(func.count())
            .select_from(OrderLine)
            .join(Partner, Partner.partner_id == OrderLine.partner_id)
            .join(Product, Product.product_id == OrderLine.product_id)
        )
        if conds:
            count_stmt = count_stmt.where(*conds)

        total = db.execute(count_stmt).scalar_one()

        # paging + ordering
        stmt = stmt.order_by(OrderLine.due_date.asc(), OrderLine.order_no.asc(), OrderLine.line_no.asc())
        stmt = stmt.offset((page - 1) * size).limit(size)

        rows = db.execute(stmt).all()

        items: List[dict] = []
        for ol, partner_name, product_code, product_name in rows:
            d = {
                # ORM -> dict for response
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
            }
            items.append(d)

        return items, total


order_line_crud = OrderLineCRUD()