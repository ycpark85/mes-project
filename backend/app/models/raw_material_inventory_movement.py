from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RawMaterialInventoryMovement(Base):
    __tablename__ = "raw_material_inventory_movement"
    __table_args__ = (
        CheckConstraint(
            "movement_type IN ('INBOUND','TRANSFER_OUT','TRANSFER_IN','ADJUST_IN','ADJUST_OUT','CONSUME_OUT','CONSUME_REVERSE')",
            name="ck_raw_material_inventory_movement__movement_type",
        ),
        CheckConstraint("qty <> 0", name="ck_raw_material_inventory_movement__qty_not_zero"),
        CheckConstraint(
            "amount_snapshot IS NULL OR amount_snapshot >= 0",
            name="ck_raw_material_inventory_movement__amount_snapshot_ge_0",
        ),
        Index("ix_raw_material_inventory_movement__material_id", "raw_material_id"),
        Index("ix_raw_material_inventory_movement__location_id", "raw_material_location_id"),
        Index("ix_raw_material_inventory_movement__lot_id", "raw_material_inventory_lot_id"),
        Index("ix_raw_material_inventory_movement__created_at", "created_at"),
        Index("ix_raw_material_inventory_movement__transfer_key", "transfer_key"),
    )

    raw_material_inventory_movement_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
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
    raw_material_inventory_lot_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("raw_material_inventory_lot.raw_material_inventory_lot_id", ondelete="SET NULL"),
        nullable=True,
    )
    lot_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    movement_type: Mapped[str] = mapped_column(String(30), nullable=False)
    qty: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    balance_after: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    unit_cost_snapshot: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    amount_snapshot: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    source_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    source_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    transfer_key: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    memo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    raw_material = relationship("RawMaterial")
    location = relationship("RawMaterialLocation")
    inventory_lot = relationship("RawMaterialInventoryLot")
