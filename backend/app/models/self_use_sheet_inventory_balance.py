from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SelfUseSheetInventoryBalance(Base):
    __tablename__ = "self_use_sheet_inventory_balance"
    __table_args__ = (
        UniqueConstraint(
            "self_use_sheet_inventory_lot_id",
            "raw_material_location_id",
            name="uq_self_use_sheet_inv_balance__lot_location",
        ),
        CheckConstraint("current_qty >= 0", name="ck_self_use_sheet_inv_balance__qty_ge_0"),
        Index("ix_self_use_sheet_inv_balance__lot_id", "self_use_sheet_inventory_lot_id"),
        Index("ix_self_use_sheet_inv_balance__location_id", "raw_material_location_id"),
    )

    self_use_sheet_inventory_balance_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    self_use_sheet_inventory_lot_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("self_use_sheet_inventory_lot.self_use_sheet_inventory_lot_id", ondelete="CASCADE"),
        nullable=False,
    )
    raw_material_location_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("raw_material_location.raw_material_location_id", ondelete="RESTRICT"),
        nullable=False,
    )
    current_qty: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    inventory_lot = relationship("SelfUseSheetInventoryLot", back_populates="location_balances")
    location = relationship("RawMaterialLocation")
