from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class OutsourceWorkGroupRawMaterialAllocation(Base):
    __tablename__ = "outsource_work_group_raw_material_allocation"
    __table_args__ = (
        CheckConstraint(
            "qty > 0",
            name="ck_owg_rm_alloc__qty_gt_0",
        ),
        CheckConstraint(
            "amount_snapshot IS NULL OR amount_snapshot >= 0",
            name="ck_owg_rm_alloc__amount_snapshot_ge_0",
        ),
        CheckConstraint(
            "status IN ('CONSUMED','REVERSED')",
            name="ck_owg_rm_alloc__status",
        ),
        Index(
            "ix_owg_raw_material_allocation__work_group_id",
            "outsource_work_group_id",
        ),
        Index(
            "ix_owg_raw_material_allocation__material_id",
            "raw_material_id",
        ),
        Index(
            "ix_owg_raw_material_allocation__location_id",
            "raw_material_location_id",
        ),
        Index(
            "ix_owg_raw_material_allocation__inventory_lot_id",
            "raw_material_inventory_lot_id",
        ),
        Index(
            "ix_owg_raw_material_allocation__movement_id",
            "raw_material_inventory_movement_id",
        ),
    )

    outsource_work_group_raw_material_allocation_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )
    outsource_work_group_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("outsource_work_group.outsource_work_group_id", ondelete="CASCADE"),
        nullable=False,
    )
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
    raw_material_inventory_movement_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("raw_material_inventory_movement.raw_material_inventory_movement_id", ondelete="SET NULL"),
        nullable=True,
    )
    lot_no: Mapped[str] = mapped_column(String(100), nullable=False)
    qty: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    unit_cost_snapshot: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    amount_snapshot: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="CONSUMED")
    memo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    work_group = relationship("OutsourceWorkGroup")
    raw_material = relationship("RawMaterial")
    location = relationship("RawMaterialLocation")
    inventory_lot = relationship("RawMaterialInventoryLot")
    movement = relationship("RawMaterialInventoryMovement")
