from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RawMaterialInventoryLot(Base):
    __tablename__ = "raw_material_inventory_lot"
    __table_args__ = (
        UniqueConstraint(
            "raw_material_id",
            "raw_material_location_id",
            "lot_no",
            name="uq_raw_material_inventory_lot__material_location_lot",
        ),
        Index("ix_raw_material_inventory_lot__material_id", "raw_material_id"),
        Index("ix_raw_material_inventory_lot__location_id", "raw_material_location_id"),
        Index("ix_raw_material_inventory_lot__lot_no", "lot_no"),
    )

    raw_material_inventory_lot_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    raw_material_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("raw_material.raw_material_id", ondelete="RESTRICT"),
        nullable=False,
    )
    raw_material_location_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("raw_material_location.raw_material_location_id", ondelete="RESTRICT"),
        nullable=False,
    )
    lot_no: Mapped[str] = mapped_column(String(100), nullable=False)
    current_qty: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    unit_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    received_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    raw_material = relationship("RawMaterial")
    location = relationship("RawMaterialLocation")
