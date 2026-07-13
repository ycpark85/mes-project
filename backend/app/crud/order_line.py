from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.models.order_line import OrderLine


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


order_line_crud = OrderLineCRUD()
