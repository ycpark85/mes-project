from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ProductionProgressSnapshot(Base):
    __tablename__ = "production_progress_snapshot"
    __table_args__ = (
        UniqueConstraint(
            "order_line_id",
            name="uq_production_progress_snapshot__order_line_id",
        ),
        CheckConstraint(
            "status IN ('IN_PROGRESS','COMPLETED')",
            name="ck_production_progress_snapshot__status",
        ),
        CheckConstraint(
            "work_type IN ('BASIC','REWORK')",
            name="ck_production_progress_snapshot__work_type",
        ),
        CheckConstraint(
            "current_process IN ('LOT_CREATED','OUTSOURCE_ORDERED','DIECUT_RECEIVED','OUTSOURCE_DONE','INSPECTION_WAITING','INSPECTION_IN_PROGRESS','COMPLETED')",
            name="ck_production_progress_snapshot__current_process",
        ),
        CheckConstraint(
            "current_process_order BETWEEN 1 AND 7",
            name="ck_production_progress_snapshot__process_order",
        ),
        CheckConstraint(
            "progress_rate BETWEEN 0 AND 100",
            name="ck_production_progress_snapshot__progress_rate",
        ),
        CheckConstraint(
            "order_qty >= 0 AND available_inventory_qty >= 0 AND production_qty >= 0",
            name="ck_production_progress_snapshot__quantities_nonnegative",
        ),
        Index("ix_production_progress_snapshot__status_due", "status", "due_date"),
        Index("ix_production_progress_snapshot__partner_status_due", "partner_id", "status", "due_date"),
        Index("ix_production_progress_snapshot__product_status_due", "product_id", "status", "due_date"),
        Index("ix_production_progress_snapshot__process_status", "current_process", "status"),
        Index("ix_production_progress_snapshot__updated_at", "updated_at"),
    )

    production_progress_snapshot_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    order_line_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("order_line.order_line_id", ondelete="CASCADE"),
        nullable=False,
    )
    order_no: Mapped[str] = mapped_column(String(40), nullable=False)
    line_no: Mapped[int] = mapped_column(Integer, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)

    partner_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("partner.partner_id", ondelete="RESTRICT"),
        nullable=False,
    )
    partner_name: Mapped[str] = mapped_column(String(200), nullable=False)

    product_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("product.product_id", ondelete="RESTRICT"),
        nullable=False,
    )
    product_code: Mapped[str] = mapped_column(String(80), nullable=False)
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)

    order_qty: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    available_inventory_qty: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    production_qty: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    work_type: Mapped[str] = mapped_column(String(20), nullable=False)
    current_process: Mapped[str] = mapped_column(String(40), nullable=False)
    current_process_order: Mapped[int] = mapped_column(Integer, nullable=False)
    progress_rate: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)

    lot_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    target_lot_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_lot_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lot_nos_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

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

    order_line = relationship("OrderLine")
    partner = relationship("Partner")
    product = relationship("Product")
