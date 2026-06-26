from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, Index, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RawMaterial(Base):
    __tablename__ = "raw_material"
    __table_args__ = (
        UniqueConstraint("material_code", name="uq_raw_material__material_code"),
        CheckConstraint("standard_unit_cost IS NULL OR standard_unit_cost >= 0", name="ck_raw_material__standard_unit_cost_ge_0"),
        Index("ix_raw_material__is_active", "is_active"),
        Index("ix_raw_material__material_name", "material_name"),
    )

    raw_material_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    material_code: Mapped[str] = mapped_column(String(60), nullable=False)
    material_name: Mapped[str] = mapped_column(String(200), nullable=False)
    material_spec: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    width_mm: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    material_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    uom: Mapped[str] = mapped_column(String(10), nullable=False, default="M")
    standard_unit_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    memo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
