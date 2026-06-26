from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Numeric, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RawMaterialInventory(Base):
    __tablename__ = "raw_material_inventory"
    __table_args__ = (
        UniqueConstraint(
            "raw_material_id",
            "raw_material_location_id",
            name="uq_raw_material_inventory__material_location",
        ),
        Index("ix_raw_material_inventory__material_id", "raw_material_id"),
        Index("ix_raw_material_inventory__location_id", "raw_material_location_id"),
    )

    raw_material_inventory_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
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
    current_qty: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    raw_material = relationship("RawMaterial")
    location = relationship("RawMaterialLocation")
