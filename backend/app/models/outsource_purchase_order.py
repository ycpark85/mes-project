from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class OutsourcePurchaseOrder(Base):
    __tablename__ = "outsource_purchase_order"
    __table_args__ = (
        CheckConstraint(
            "process_type IN ('CUT','PRINT')",
            name="ck_outsource_purchase_order__process_type",
        ),
        CheckConstraint("qty > 0", name="ck_outsource_purchase_order__qty_gt_0"),
        CheckConstraint(
            "unit_price IS NULL OR unit_price >= 0",
            name="ck_outsource_purchase_order__unit_price_ge_0",
        ),
        CheckConstraint(
            "supply_amount IS NULL OR supply_amount >= 0",
            name="ck_outsource_purchase_order__supply_amount_ge_0",
        ),
        CheckConstraint(
            "vat_amount IS NULL OR vat_amount >= 0",
            name="ck_outsource_purchase_order__vat_amount_ge_0",
        ),
        CheckConstraint(
            "total_amount IS NULL OR total_amount >= 0",
            name="ck_outsource_purchase_order__total_amount_ge_0",
        ),
        Index("ix_outsource_purchase_order__purchase_order_no", "purchase_order_no"),
        Index("ix_outsource_purchase_order__purchase_order_date", "purchase_order_date"),
        Index("ix_outsource_purchase_order__process_type", "process_type"),
        Index("ix_outsource_purchase_order__outsource_partner_id", "outsource_partner_id"),
        Index("ix_outsource_purchase_order__inbound_partner_id", "inbound_partner_id"),
    )

    outsource_purchase_order_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )

    purchase_order_no: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        unique=True,
    )

    purchase_order_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    process_type: Mapped[str] = mapped_column(String(20), nullable=False)

    outsource_partner_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("partner.partner_id", ondelete="RESTRICT"),
        nullable=False,
    )

    inbound_partner_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("partner.partner_id", ondelete="RESTRICT"),
        nullable=True,
    )

    work_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    form_snapshot_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    qty: Mapped[int] = mapped_column(BigInteger, nullable=False)

    unit_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    supply_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    vat_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    total_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)

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

    outsource_partner = relationship(
        "Partner",
        foreign_keys=[outsource_partner_id],
    )

    inbound_partner = relationship(
        "Partner",
        foreign_keys=[inbound_partner_id],
    )

    items: Mapped[List["OutsourcePurchaseOrderItem"]] = relationship(
    "OutsourcePurchaseOrderItem",
    back_populates="purchase_order",
    cascade="all, delete-orphan",
)