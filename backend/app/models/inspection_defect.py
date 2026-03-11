from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class InspectionDefect(Base):
    """회차별 불량 내역 (inspection_result 기준)"""

    __tablename__ = "inspection_defect"
    __table_args__ = (
        CheckConstraint("defect_qty >= 0", name="ck_inspection_defect__defect_qty"),
        CheckConstraint(
            "disposition IN ('SHIP_AS_IS','NOT_SHIPPABLE')",
            name="ck_inspection_defect__disposition",
        ),
        Index("ix_inspection_defect__inspection_result_id", "inspection_result_id"),
        Index("ix_inspection_defect__defect_type_id", "defect_type_id"),
    )

    inspection_defect_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    inspection_result_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("inspection_result.inspection_result_id", ondelete="CASCADE"),
        nullable=False,
    )

    defect_type_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("defect_type.defect_type_id", ondelete="RESTRICT"),
        nullable=False,
    )

    defect_qty: Mapped[int] = mapped_column(Integer, nullable=False)
    disposition: Mapped[str] = mapped_column(String(20), nullable=False, default="NOT_SHIPPABLE")
    memo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    inspection_result = relationship("InspectionResult", back_populates="defects")
    defect_type = relationship("DefectType")

    attachments: Mapped[List["InspectionDefectAttachment"]] = relationship(
        "InspectionDefectAttachment",
        back_populates="inspection_defect",
        cascade="all, delete-orphan",
    )