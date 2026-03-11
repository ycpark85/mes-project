from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    Index,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class InspectionCertificate(Base):
    """
    성적서 (LOT 완료 SSOT)
    - LOT당 1회만 발행 가능
    """

    __tablename__ = "inspection_certificate"
    __table_args__ = (
        UniqueConstraint("lot_id", name="uq_inspection_certificate__lot"),
        Index("ix_inspection_certificate__issued_at", "issued_at"),
    )

    inspection_certificate_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    lot_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("lot.lot_id", ondelete="RESTRICT"),
        nullable=False,
    )

    basis_inspection_result_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("inspection_result.inspection_result_id", ondelete="RESTRICT"),
        nullable=False,
    )

    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    issued_by: Mapped[str] = mapped_column(String(50), nullable=False)

    memo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    lot = relationship("Lot")
    basis_inspection_result = relationship("InspectionResult")