from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    String,
    Text,
    Index,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class InspectionDefectAttachment(Base):
    """
    불량 항목별 첨부 (사진/파일)
    """

    __tablename__ = "inspection_defect_attachment"
    __table_args__ = (
        Index("ix_inspection_defect_attachment__inspection_defect_id", "inspection_defect_id"),
    )

    inspection_defect_attachment_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    inspection_defect_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("inspection_defect.inspection_defect_id", ondelete="CASCADE"),
        nullable=False,
    )

    file_uri: Mapped[str] = mapped_column(String(600), nullable=False)
    file_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    memo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    inspection_defect = relationship("InspectionDefect", back_populates="attachments")