from __future__ import annotations

from datetime import date
from typing import Optional, Tuple, List

from sqlalchemy.orm import Session

from app.models.order_line import OrderLine
from app.services.order_line_list_query import list_order_lines_for_grid


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
        for key, value in data.items():
            setattr(obj, key, value)
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
        return list_order_lines_for_grid(
            db,
            page=page,
            size=size,
            q=q,
            status=status,
            status_group=status_group,
            is_active=is_active,
            partner_id=partner_id,
            product_id=product_id,
            order_date_from=order_date_from,
            order_date_to=order_date_to,
            due_date_from=due_date_from,
            due_date_to=due_date_to,
        )


order_line_crud = OrderLineCRUD()
