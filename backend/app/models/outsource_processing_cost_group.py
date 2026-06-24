from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    Index,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class OutsourceProcessingCostGroup(Base):
    __tablename__ = "outsource_processing_cost_group"
    __table_args__ = (
        CheckConstraint(
            "process_type IN ('CUT','PRINT','DIECUT')",
            name="ck_outsource_processing_cost_group__process_type",
        ),
        CheckConstraint(
            "status IN ('DRAFT','CLOSED','CANCELED')",
            name="ck_outsource_processing_cost_group__status",
        ),
        CheckConstraint(
            "standard_amount IS NULL OR standard_amount >= 0",
            name="ck_outsource_processing_cost_group__standard_amount_ge_0",
        ),
        CheckConstraint(
            "actual_amount IS NULL OR actual_amount >= 0",
            name="ck_outsource_processing_cost_group__actual_amount_ge_0",
        ),
        Index(
            "ix_outsource_processing_cost_group__settlement_month",
            "settlement_month",
        ),
        Index(
            "ix_outsource_processing_cost_group__process_status",
            "process_type",
            "status",
        ),
        Index(
            "ix_outsource_processing_cost_group__cost_group_no",
            "cost_group_no",
        ),
    )

    outsource_processing_cost_group_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )
    cost_group_no: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    settlement_month: Mapped[date] = mapped_column(Date, nullable=False)
    process_type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")

    standard_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(18, 2),
        nullable=True,
    )
    standard_memo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    actual_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(18, 2),
        nullable=True,
    )
    actual_billing_month: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    actual_memo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    closed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    canceled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
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

    work_groups: Mapped[List["OutsourceProcessingCostWorkGroup"]] = relationship(
        "OutsourceProcessingCostWorkGroup",
        back_populates="cost_group",
        cascade="all, delete-orphan",
    )
    allocations: Mapped[List["OutsourceProcessingCostAllocation"]] = relationship(
        "OutsourceProcessingCostAllocation",
        back_populates="cost_group",
        cascade="all, delete-orphan",
    )
