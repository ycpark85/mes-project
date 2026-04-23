from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class OutsourcePurchaseOrderGroup(Base):
    __tablename__ = "outsource_purchase_order_group"
    __table_args__ = (
        CheckConstraint(
            "status IS NULL OR status IN ('VENDOR_RECEIVED','WORK_DONE','SHIPPED')",
            name="ck_outsource_purchase_order_group__status",
        ),
        Index(
            "ix_outsource_purchase_order_group__purchase_order_id",
            "outsource_purchase_order_id",
        ),
        Index(
            "ix_outsource_purchase_order_group__work_group_id",
            "outsource_work_group_id",
        ),
        Index(
            "ix_outsource_purchase_order_group__status",
            "status",
        ),
    )

    outsource_purchase_order_group_id: Mapped[int] = mapped_column(
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

    outsource_work_group_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "outsource_work_group.outsource_work_group_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    item_seq: Mapped[int] = mapped_column(Integer, nullable=False)
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

    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    purchase_order = relationship("OutsourcePurchaseOrder")

    work_group = relationship(
        "OutsourceWorkGroup",
        back_populates="purchase_order_groups",
    )