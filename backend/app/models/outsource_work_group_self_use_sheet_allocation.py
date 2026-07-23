from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class OutsourceWorkGroupSelfUseSheetAllocation(Base):
    __tablename__ = "outsource_work_group_self_use_sheet_allocation"
    __table_args__ = (
        CheckConstraint("qty > 0", name="ck_owg_self_use_sheet_alloc__qty_gt_0"),
        CheckConstraint("unit_cost_snapshot >= 0", name="ck_owg_self_use_sheet_alloc__unit_cost_ge_0"),
        CheckConstraint("amount_snapshot >= 0", name="ck_owg_self_use_sheet_alloc__amount_ge_0"),
        CheckConstraint(
            "status IN ('CONSUMED','REVERSED')",
            name="ck_owg_self_use_sheet_alloc__status",
        ),
        Index("ix_owg_self_use_sheet_alloc__group_id", "outsource_work_group_id"),
        Index("ix_owg_self_use_sheet_alloc__lot_id", "self_use_sheet_inventory_lot_id"),
        Index("ix_owg_self_use_sheet_alloc__movement_id", "inventory_movement_id"),
    )

    outsource_work_group_self_use_sheet_allocation_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    outsource_work_group_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("outsource_work_group.outsource_work_group_id", ondelete="CASCADE"),
        nullable=False,
    )
    self_use_sheet_inventory_lot_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("self_use_sheet_inventory_lot.self_use_sheet_inventory_lot_id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_location_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("raw_material_location.raw_material_location_id", ondelete="RESTRICT"),
        nullable=False,
    )
    sheet_lot_no: Mapped[str] = mapped_column(String(50), nullable=False)
    qty: Mapped[int] = mapped_column(BigInteger, nullable=False)
    unit_cost_snapshot: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    amount_snapshot: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    inventory_movement_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("self_use_sheet_inventory_movement.self_use_sheet_inventory_movement_id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="CONSUMED")
    memo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    work_group = relationship("OutsourceWorkGroup", back_populates="self_use_sheet_allocations")
    inventory_lot = relationship("SelfUseSheetInventoryLot")
    source_location = relationship("RawMaterialLocation")
    inventory_movement = relationship("SelfUseSheetInventoryMovement")
    source_snapshots = relationship(
        "OutsourceWorkGroupSelfUseSheetSourceSnapshot",
        back_populates="allocation",
        cascade="all, delete-orphan",
    )
