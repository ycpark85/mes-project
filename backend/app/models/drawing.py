# app/models/drawing.py
from __future__ import annotations

from datetime import datetime
from typing import Optional, List

from sqlalchemy import BigInteger, Boolean, DateTime, String, ForeignKey, func, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Drawing(Base):
    __tablename__ = "drawing"
    __table_args__ = (
        UniqueConstraint("drawing_no", name="uq_drawing__drawing_no"),
        Index("ix_drawing__is_active", "is_active"),
    )

    drawing_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    drawing_no: Mapped[str] = mapped_column(String(60), nullable=False)

    # 최신 리비전 포인터 (자동 갱신)
    current_revision_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("drawing_revision.revision_id", ondelete="SET NULL"),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # 관계
    revisions: Mapped[List["DrawingRevision"]] = relationship(
        "DrawingRevision",
        back_populates="drawing",
        cascade="all, delete-orphan",
        foreign_keys="DrawingRevision.drawing_id"
    )

    current_revision: Mapped[Optional["DrawingRevision"]] = relationship(
        "DrawingRevision",
        foreign_keys=[current_revision_id],
        post_update=True,  # 순환참조 업데이트 안전
    )
    @property
    def current_revision_no(self) -> str | None:
        return self.current_revision.rev_no if self.current_revision else None

    product: Mapped[Optional["Product"]] = relationship(
        "Product",
        back_populates="drawing",
        uselist=False,  # 1:1
    )