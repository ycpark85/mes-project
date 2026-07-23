from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SelfUseSheetInventoryMovement(Base):
    __tablename__ = "self_use_sheet_inventory_movement"
    __table_args__ = (
        UniqueConstraint("source_movement_id", name="uq_self_use_sheet_inv_movement__source_movement_id"),
        CheckConstraint(
            "movement_type IN ('PRODUCE_IN','USE_OUT','USE_REVERSE','CANCEL_OUT','TRANSFER_OUT','TRANSFER_IN','WORK_USE_OUT','WORK_USE_REVERSE')",
            name="ck_self_use_sheet_inv_movement__movement_type",
        ),
        CheckConstraint("qty <> 0", name="ck_self_use_sheet_inv_movement__qty_not_zero"),
        CheckConstraint("balance_after >= 0", name="ck_self_use_sheet_inv_movement__balance_ge_0"),
        CheckConstraint("amount_snapshot >= 0", name="ck_self_use_sheet_inv_movement__amount_ge_0"),
        CheckConstraint(
            "purpose_type IS NULL OR purpose_type IN ('PRINT_SETUP','SAMPLE','TEST_RND','OTHER')",
            name="ck_self_use_sheet_inv_movement__purpose_type",
        ),
        Index("ix_self_use_sheet_inv_movement__lot_id", "self_use_sheet_inventory_lot_id"),
        Index("ix_self_use_sheet_inv_movement__location_id", "raw_material_location_id"),
        Index("ix_self_use_sheet_inv_movement__created_at", "created_at"),
    )

    self_use_sheet_inventory_movement_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    self_use_sheet_inventory_lot_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("self_use_sheet_inventory_lot.self_use_sheet_inventory_lot_id", ondelete="CASCADE"),
        nullable=False,
    )
    movement_type: Mapped[str] = mapped_column(String(20), nullable=False)
    raw_material_location_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("raw_material_location.raw_material_location_id", ondelete="RESTRICT"),
        nullable=False,
    )
    counterpart_location_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("raw_material_location.raw_material_location_id", ondelete="RESTRICT"),
        nullable=True,
    )
    qty: Mapped[int] = mapped_column(BigInteger, nullable=False)
    balance_after: Mapped[int] = mapped_column(BigInteger, nullable=False)
    location_balance_after: Mapped[int] = mapped_column(BigInteger, nullable=False)
    purpose_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    unit_cost_snapshot: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    amount_snapshot: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    source_movement_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("self_use_sheet_inventory_movement.self_use_sheet_inventory_movement_id", ondelete="RESTRICT"),
        nullable=True,
    )
    source_type: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    source_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    transfer_key: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    memo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    inventory_lot = relationship("SelfUseSheetInventoryLot", back_populates="movements")
    source_movement = relationship("SelfUseSheetInventoryMovement", remote_side=[self_use_sheet_inventory_movement_id])
    location = relationship("RawMaterialLocation", foreign_keys=[raw_material_location_id])
    counterpart_location = relationship("RawMaterialLocation", foreign_keys=[counterpart_location_id])
