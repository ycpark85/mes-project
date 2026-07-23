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
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SelfUseSheetJob(Base):
    __tablename__ = "self_use_sheet_job"
    __table_args__ = (
        UniqueConstraint("use_no", name="uq_self_use_sheet_job__use_no"),
        CheckConstraint(
            "purpose_type IN ('PRINT_SETUP','SAMPLE','TEST_RND','OTHER')",
            name="ck_self_use_sheet_job__purpose_type",
        ),
        CheckConstraint(
            "purpose_type <> 'OTHER' OR NULLIF(TRIM(memo), '') IS NOT NULL",
            name="ck_self_use_sheet_job__other_memo_required",
        ),
        CheckConstraint(
            "execution_type IN ('INTERNAL','OUTSOURCE')",
            name="ck_self_use_sheet_job__execution_type",
        ),
        CheckConstraint(
            "status IN ('DRAFT','IN_PROGRESS','COMPLETED','CANCELED')",
            name="ck_self_use_sheet_job__status",
        ),
        CheckConstraint(
            "execution_type <> 'OUTSOURCE' OR partner_id IS NOT NULL",
            name="ck_self_use_sheet_job__outsource_partner_required",
        ),
        CheckConstraint("cut_width_mm > 0", name="ck_self_use_sheet_job__cut_width_gt_0"),
        CheckConstraint("cut_length_mm > 0", name="ck_self_use_sheet_job__cut_length_gt_0"),
        CheckConstraint(
            "planned_output_qty > 0",
            name="ck_self_use_sheet_job__planned_output_qty_gt_0",
        ),
        CheckConstraint(
            "expected_processing_fee >= 0",
            name="ck_self_use_sheet_job__expected_fee_ge_0",
        ),
        CheckConstraint(
            "actual_processing_fee IS NULL OR actual_processing_fee >= 0",
            name="ck_self_use_sheet_job__actual_fee_ge_0",
        ),
        CheckConstraint(
            "actual_input_qty IS NULL OR actual_input_qty > 0",
            name="ck_self_use_sheet_job__actual_input_qty_gt_0",
        ),
        CheckConstraint(
            "produced_qty IS NULL OR produced_qty > 0",
            name="ck_self_use_sheet_job__produced_qty_gt_0",
        ),
        CheckConstraint(
            "scrap_qty IS NULL OR scrap_qty >= 0",
            name="ck_self_use_sheet_job__scrap_qty_ge_0",
        ),
        CheckConstraint("version >= 1", name="ck_self_use_sheet_job__version_positive"),
        CheckConstraint(
            "status <> 'IN_PROGRESS' OR (started_at IS NOT NULL AND started_by IS NOT NULL)",
            name="ck_self_use_sheet_job__in_progress_audit_required",
        ),
        CheckConstraint(
            "status <> 'COMPLETED' OR (actual_processing_fee IS NOT NULL AND actual_input_qty IS NOT NULL AND produced_qty IS NOT NULL AND completed_at IS NOT NULL AND completed_by IS NOT NULL)",
            name="ck_self_use_sheet_job__completion_required",
        ),
        CheckConstraint(
            "status <> 'CANCELED' OR (canceled_at IS NOT NULL AND canceled_by IS NOT NULL AND NULLIF(TRIM(cancel_reason), '') IS NOT NULL)",
            name="ck_self_use_sheet_job__cancel_audit_required",
        ),
        Index("ix_self_use_sheet_job__status", "status"),
        Index("ix_self_use_sheet_job__purpose_type", "purpose_type"),
        Index("ix_self_use_sheet_job__partner_id", "partner_id"),
        Index("ix_self_use_sheet_job__created_at", "created_at"),
    )

    self_use_sheet_job_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    use_no: Mapped[str] = mapped_column(String(40), nullable=False)
    purpose_type: Mapped[str] = mapped_column(String(30), nullable=False)
    execution_type: Mapped[str] = mapped_column(String(20), nullable=False)
    partner_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("partner.partner_id", ondelete="RESTRICT"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")
    cut_width_mm: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    cut_length_mm: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    planned_output_qty: Mapped[int] = mapped_column(BigInteger, nullable=False)
    expected_processing_fee: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    actual_processing_fee: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    actual_input_qty: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    produced_qty: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    scrap_qty: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    memo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cancel_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(100), nullable=False)
    started_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    completed_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    canceled_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    canceled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    partner = relationship("Partner")
    allocations = relationship(
        "SelfUseSheetRawMaterialAllocation",
        back_populates="job",
        cascade="all, delete-orphan",
    )
    sheet_lot = relationship("SelfUseSheetInventoryLot", back_populates="job", uselist=False)
