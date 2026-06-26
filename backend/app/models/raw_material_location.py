from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RawMaterialLocation(Base):
    __tablename__ = "raw_material_location"
    __table_args__ = (
        UniqueConstraint("location_code", name="uq_raw_material_location__location_code"),
        CheckConstraint(
            "location_type IN ('INTERNAL_WAREHOUSE','OUTSOURCE_VENDOR','OTHER')",
            name="ck_raw_material_location__location_type",
        ),
        Index("ix_raw_material_location__is_active", "is_active"),
        Index("ix_raw_material_location__partner_id", "partner_id"),
    )

    raw_material_location_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    location_code: Mapped[str] = mapped_column(String(60), nullable=False)
    location_name: Mapped[str] = mapped_column(String(200), nullable=False)
    location_type: Mapped[str] = mapped_column(String(30), nullable=False)
    partner_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("partner.partner_id", ondelete="RESTRICT"),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    memo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    partner = relationship("Partner")
