from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class DrawingRevisionFile(Base):
    __tablename__ = "drawing_revision_file"
    __table_args__ = (
        UniqueConstraint(
            "revision_id",
            "file_kind",
            name="uq_drawing_revision_file__revision_id__file_kind",
        ),
        Index("ix_drawing_revision_file__revision_id", "revision_id"),
        Index("ix_drawing_revision_file__file_kind", "file_kind"),
    )

    revision_file_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    revision_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("drawing_revision.revision_id", ondelete="CASCADE"),
        nullable=False,
    )

    file_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    file_uri: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    revision = relationship("DrawingRevision", back_populates="files")