from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SelfUseSheetInventoryLot(Base):
    __tablename__ = "self_use_sheet_inventory_lot"
    __table_args__ = (
        UniqueConstraint("self_use_sheet_job_id", name="uq_self_use_sheet_inventory_lot__job_id"),
        UniqueConstraint("sheet_lot_no", name="uq_self_use_sheet_inventory_lot__lot_no"),
        CheckConstraint("initial_qty > 0", name="ck_self_use_sheet_inventory_lot__initial_qty_gt_0"),
        CheckConstraint("current_qty >= 0", name="ck_self_use_sheet_inventory_lot__current_qty_ge_0"),
        CheckConstraint("current_qty <= initial_qty", name="ck_self_use_sheet_inventory_lot__current_qty_le_initial"),
        CheckConstraint("material_amount >= 0", name="ck_self_use_sheet_inventory_lot__material_amount_ge_0"),
        CheckConstraint("processing_fee >= 0", name="ck_self_use_sheet_inventory_lot__processing_fee_ge_0"),
        CheckConstraint("total_cost >= 0", name="ck_self_use_sheet_inventory_lot__total_cost_ge_0"),
        CheckConstraint("unit_cost >= 0", name="ck_self_use_sheet_inventory_lot__unit_cost_ge_0"),
        CheckConstraint(
            "status IN ('AVAILABLE','DEPLETED','CANCELED')",
            name="ck_self_use_sheet_inventory_lot__status",
        ),
        CheckConstraint("version >= 1", name="ck_self_use_sheet_inventory_lot__version_positive"),
        Index("ix_self_use_sheet_inventory_lot__material_id", "raw_material_id"),
        Index("ix_self_use_sheet_inventory_lot__status", "status"),
        Index("ix_self_use_sheet_inventory_lot__completed_at", "completed_at"),
    )

    self_use_sheet_inventory_lot_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    self_use_sheet_job_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("self_use_sheet_job.self_use_sheet_job_id", ondelete="RESTRICT"),
        nullable=False,
    )
    raw_material_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("raw_material.raw_material_id", ondelete="RESTRICT"),
        nullable=False,
    )
    sheet_lot_no: Mapped[str] = mapped_column(String(50), nullable=False)
    source_lot_summary: Mapped[str] = mapped_column(Text, nullable=False)
    cut_width_mm: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    cut_length_mm: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    initial_qty: Mapped[int] = mapped_column(BigInteger, nullable=False)
    current_qty: Mapped[int] = mapped_column(BigInteger, nullable=False)
    material_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    processing_fee: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="AVAILABLE")
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    job = relationship("SelfUseSheetJob", back_populates="sheet_lot")
    raw_material = relationship("RawMaterial")
    movements = relationship(
        "SelfUseSheetInventoryMovement",
        back_populates="inventory_lot",
        cascade="all, delete-orphan",
    )
    location_balances = relationship(
        "SelfUseSheetInventoryBalance",
        back_populates="inventory_lot",
        cascade="all, delete-orphan",
    )
