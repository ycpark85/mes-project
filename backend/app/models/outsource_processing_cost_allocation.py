from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class OutsourceProcessingCostAllocation(Base):
    __tablename__ = "outsource_processing_cost_allocation"
    __table_args__ = (
        CheckConstraint(
            "basis_type IN ('QUANTITY','AREA')",
            name="ck_outsource_processing_cost_allocation__basis_type",
        ),
        CheckConstraint(
            "basis_value >= 0",
            name="ck_outsource_processing_cost_allocation__basis_value_ge_0",
        ),
        CheckConstraint(
            "allocation_ratio >= 0",
            name="ck_outsource_processing_cost_allocation__allocation_ratio_ge_0",
        ),
        CheckConstraint(
            "standard_allocated_amount IS NULL OR standard_allocated_amount >= 0",
            name="ck_outsource_processing_cost_allocation__standard_amount_ge_0",
        ),
        CheckConstraint(
            "actual_allocated_amount IS NULL OR actual_allocated_amount >= 0",
            name="ck_outsource_processing_cost_allocation__actual_amount_ge_0",
        ),
        Index(
            "ix_outsource_processing_cost_allocation__cost_group_id",
            "outsource_processing_cost_group_id",
        ),
        Index(
            "ix_outsource_processing_cost_allocation__lot_id",
            "lot_id",
        ),
        Index(
            "ix_outsource_processing_cost_allocation__work_group_item_id",
            "outsource_work_group_item_id",
        ),
    )

    outsource_processing_cost_allocation_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )
    outsource_processing_cost_group_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "outsource_processing_cost_group.outsource_processing_cost_group_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    outsource_work_group_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("outsource_work_group.outsource_work_group_id", ondelete="SET NULL"),
        nullable=True,
    )
    outsource_work_group_item_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey(
            "outsource_work_group_item.outsource_work_group_item_id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )
    lot_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("lot.lot_id", ondelete="RESTRICT"),
        nullable=False,
    )

    lot_no_snapshot: Mapped[str] = mapped_column(String(20), nullable=False)
    product_code_snapshot: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    product_name_snapshot: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    product_spec_snapshot: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    panel_width_mm_snapshot: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    panel_length_mm_snapshot: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cuts_per_sheet_snapshot: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sheet_qty_snapshot: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    instruction_output_qty_snapshot: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True,
    )
    basis_type: Mapped[str] = mapped_column(String(20), nullable=False)
    basis_value: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    basis_area_sqm: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 6), nullable=True)
    allocation_ratio: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    standard_allocated_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(18, 2),
        nullable=True,
    )
    actual_allocated_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(18, 2),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    cost_group = relationship(
        "OutsourceProcessingCostGroup",
        back_populates="allocations",
    )
    lot = relationship("Lot")
    work_group = relationship("OutsourceWorkGroup")
    work_group_item = relationship("OutsourceWorkGroupItem")
