from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SelfUseSheetRawMaterialAllocation(Base):
    __tablename__ = "self_use_sheet_raw_material_allocation"
    __table_args__ = (
        CheckConstraint("planned_qty > 0", name="ck_self_use_sheet_rm_alloc__planned_qty_gt_0"),
        CheckConstraint(
            "actual_consumed_qty IS NULL OR actual_consumed_qty > 0",
            name="ck_self_use_sheet_rm_alloc__actual_qty_gt_0",
        ),
        CheckConstraint(
            "returned_qty >= 0",
            name="ck_self_use_sheet_rm_alloc__returned_qty_ge_0",
        ),
        CheckConstraint(
            "status IN ('PLANNED','ISSUED','CONSUMED','REVERSED')",
            name="ck_self_use_sheet_rm_alloc__status",
        ),
        CheckConstraint(
            "status <> 'CONSUMED' OR (actual_consumed_qty IS NOT NULL AND actual_consumed_qty + returned_qty = planned_qty)",
            name="ck_self_use_sheet_rm_alloc__consumed_qty_reconciled",
        ),
        Index("ix_self_use_sheet_rm_alloc__job_id", "self_use_sheet_job_id"),
        Index("ix_self_use_sheet_rm_alloc__material_id", "raw_material_id"),
        Index("ix_self_use_sheet_rm_alloc__original_lot_id", "original_inventory_lot_id"),
        Index("ix_self_use_sheet_rm_alloc__processing_lot_id", "processing_inventory_lot_id"),
    )

    self_use_sheet_raw_material_allocation_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    self_use_sheet_job_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("self_use_sheet_job.self_use_sheet_job_id", ondelete="CASCADE"),
        nullable=False,
    )
    raw_material_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("raw_material.raw_material_id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_location_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("raw_material_location.raw_material_location_id", ondelete="RESTRICT"),
        nullable=False,
    )
    original_inventory_lot_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("raw_material_inventory_lot.raw_material_inventory_lot_id", ondelete="SET NULL"),
        nullable=True,
    )
    processing_inventory_lot_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("raw_material_inventory_lot.raw_material_inventory_lot_id", ondelete="SET NULL"),
        nullable=True,
    )
    lot_no: Mapped[str] = mapped_column(String(100), nullable=False)
    planned_qty: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    actual_consumed_qty: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    returned_qty: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    unit_cost_snapshot: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    amount_snapshot: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    issue_movement_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("raw_material_inventory_movement.raw_material_inventory_movement_id", ondelete="SET NULL"),
        nullable=True,
    )
    dispatch_transfer_key: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    return_transfer_key: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PLANNED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    job = relationship("SelfUseSheetJob", back_populates="allocations")
    raw_material = relationship("RawMaterial")
    source_location = relationship("RawMaterialLocation", foreign_keys=[source_location_id])
    original_inventory_lot = relationship("RawMaterialInventoryLot", foreign_keys=[original_inventory_lot_id])
    processing_inventory_lot = relationship("RawMaterialInventoryLot", foreign_keys=[processing_inventory_lot_id])
    issue_movement = relationship("RawMaterialInventoryMovement", foreign_keys=[issue_movement_id])
