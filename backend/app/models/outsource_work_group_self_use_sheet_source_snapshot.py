from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class OutsourceWorkGroupSelfUseSheetSourceSnapshot(Base):
    __tablename__ = "outsource_work_group_self_use_sheet_source_snapshot"
    __table_args__ = (
        Index("ix_owg_self_use_sheet_source__allocation_id", "self_use_sheet_allocation_id"),
        Index("ix_owg_self_use_sheet_source__raw_lot_id", "original_inventory_lot_id"),
    )

    outsource_work_group_self_use_sheet_source_snapshot_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )
    self_use_sheet_allocation_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "outsource_work_group_self_use_sheet_allocation.outsource_work_group_self_use_sheet_allocation_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    self_use_sheet_raw_material_allocation_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey(
            "self_use_sheet_raw_material_allocation.self_use_sheet_raw_material_allocation_id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )
    original_inventory_lot_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("raw_material_inventory_lot.raw_material_inventory_lot_id", ondelete="SET NULL"),
        nullable=True,
    )
    raw_material_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("raw_material.raw_material_id", ondelete="RESTRICT"),
        nullable=False,
    )
    raw_material_code_snapshot: Mapped[str] = mapped_column(String(100), nullable=False)
    raw_material_name_snapshot: Mapped[str] = mapped_column(String(200), nullable=False)
    raw_material_lot_no_snapshot: Mapped[str] = mapped_column(String(100), nullable=False)
    source_location_name_snapshot: Mapped[str] = mapped_column(String(200), nullable=False)
    actual_consumed_qty_snapshot: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    unit_cost_snapshot: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    amount_snapshot: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    allocation = relationship("OutsourceWorkGroupSelfUseSheetAllocation", back_populates="source_snapshots")
