from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class OutsourcePurchaseOrderItem(Base):
    __tablename__ = "outsource_purchase_order_item"
    __table_args__ = (
        CheckConstraint("qty > 0", name="ck_outsource_purchase_order_item__qty_gt_0"),
        CheckConstraint(
            "work_done_qty IS NULL OR work_done_qty >= 0",
            name="ck_outsource_purchase_order_item__work_done_qty_ge_0",
        ),
        CheckConstraint(
            "bad_qty IS NULL OR bad_qty >= 0",
            name="ck_outsource_purchase_order_item__bad_qty_ge_0",
        ),
        CheckConstraint(
            "status IS NULL OR status IN ('VENDOR_RECEIVED','WORK_DONE','SHIPPED')",
            name="ck_outsource_purchase_order_item__status",
        ),
        Index(
            "ix_outsource_purchase_order_item__purchase_order_id",
            "outsource_purchase_order_id",
        ),
        Index("ix_outsource_purchase_order_item__lot_id", "lot_id"),
        Index("ix_outsource_purchase_order_item__status", "status"),
    )

    outsource_purchase_order_item_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )

    outsource_purchase_order_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "outsource_purchase_order.outsource_purchase_order_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    lot_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("lot.lot_id", ondelete="RESTRICT"),
        nullable=False,
    )

    outsource_work_instruction_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True,
    )

    item_seq: Mapped[int] = mapped_column(nullable=False)
    qty: Mapped[int] = mapped_column(BigInteger, nullable=False)

    status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    vendor_received_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    work_done_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    shipped_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    work_done_qty: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    bad_qty: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    work_done_remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    purchase_order = relationship(
        "OutsourcePurchaseOrder",
        back_populates="items",
    )

    lot = relationship("Lot")