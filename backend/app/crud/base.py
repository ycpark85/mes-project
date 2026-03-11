# app/crud/base.py
from __future__ import annotations

from typing import Any, Iterable
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy import func, or_


class BaseCRUD:
    def __init__(
        self,
        model: Any,
        pk_field: str,
        *,
        active_field: str = "is_active",
        default_active_only: bool = True,
        q_fields: Iterable[str] = (),
        unique_conflict_message: str = "Unique constraint violated",
    ):
        self.model = model
        self.pk_field = pk_field
        self.active_field = active_field
        self.default_active_only = default_active_only
        self.q_fields = list(q_fields)
        self.unique_conflict_message = unique_conflict_message

    def _pk_col(self):
        return getattr(self.model, self.pk_field)

    def _active_col(self):
        return getattr(self.model, self.active_field)

    def get_or_404(self, db: Session, pk: int, *, active_only: bool | None = None):
        if active_only is None:
            active_only = self.default_active_only

        q = db.query(self.model).filter(self._pk_col() == pk)
        if active_only:
            q = q.filter(self._active_col() == True)
        obj = q.first()
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{self.model.__name__} not found")
        return obj

    def list_paged(
        self,
        db: Session,
        *,
        page: int,
        size: int,
        q: str | None = None,
        is_active: bool | None = True,
        order_by_desc: bool = True,
    ):
        base = db.query(self.model)

        if is_active is not None:
            base = base.filter(self._active_col() == is_active)

        if q and self.q_fields:
            like = f"%{q}%"
            conds = [getattr(self.model, f).ilike(like) for f in self.q_fields]
            base = base.filter(or_(*conds))

        total = base.with_entities(func.count()).scalar() or 0

        order_col = self._pk_col()
        base = base.order_by(order_col.desc() if order_by_desc else order_col.asc())
        items = base.offset((page - 1) * size).limit(size).all()
        return items, total

    def create(self, db: Session, obj: Any):
        try:
            db.add(obj)
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=self.unique_conflict_message)
        db.refresh(obj)
        return obj

    def commit(self, db: Session, obj: Any):
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=self.unique_conflict_message)
        db.refresh(obj)
        return obj

    def soft_delete(self, db: Session, pk: int):
        obj = self.get_or_404(db, pk, active_only=False)
        setattr(obj, self.active_field, False)
        return self.commit(db, obj)