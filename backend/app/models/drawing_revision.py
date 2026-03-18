# app/models/drawing_revision.py
from __future__ import annotations

from datetime import datetime
from typing import Optional, List

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, UniqueConstraint, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class DrawingRevision(Base):
    __tablename__ = "drawing_revision"
    __table_args__ = (
        UniqueConstraint("drawing_id", "rev_no", name="uq_drawing_revision__drawing_id__rev_no"),
        Index("ix_drawing_revision__drawing_id", "drawing_id"),
    )

    revision_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    drawing_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("drawing.drawing_id", ondelete="CASCADE"),
        nullable=False,
    )

    rev_no: Mapped[str] = mapped_column(String(20), nullable=False)  # A, B, 1, 2 등
    file_uri: Mapped[str] = mapped_column(String(500), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    drawing = relationship("Drawing", back_populates="revisions",foreign_keys=[drawing_id])

    files: Mapped[List["DrawingRevisionFile"]] = relationship(
    "DrawingRevisionFile",
    back_populates="revision",
    cascade="all, delete-orphan",
    )