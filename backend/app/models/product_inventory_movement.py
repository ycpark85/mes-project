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


class ProductInventoryMovement(Base):
    __tablename__ = "product_inventory_movement"

    __table_args__ = (
        CheckConstraint(
            "movement_type IN ('INSPECTION_IN','SHIP_OUT','ADJUST_IN','ADJUST_OUT')",
            name="ck_product_inventory_movement__movement_type",
        ),
        CheckConstraint(
            "qty <> 0",
            name="ck_product_inventory_movement__qty_not_zero",
        ),
        Index("ix_product_inventory_movement__product_id", "product_id"),
        Index("ix_product_inventory_movement__order_line_id", "order_line_id"),
        Index("ix_product_inventory_movement__inspection_result_id", "inspection_result_id"),
        Index("ix_product_inventory_movement__created_at", "created_at"),
    )

    inventory_movement_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    product_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("product.product_id", ondelete="RESTRICT"),
        nullable=False,
    )

    movement_type: Mapped[str] = mapped_column(String(30), nullable=False)
    qty: Mapped[int] = mapped_column(BigInteger, nullable=False)
    balance_after: Mapped[int] = mapped_column(BigInteger, nullable=False)

    source_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    source_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    order_line_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("order_line.order_line_id", ondelete="SET NULL"),
        nullable=True,
    )

    inspection_schedule_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("inspection_schedule.inspection_schedule_id", ondelete="SET NULL"),
        nullable=True,
    )

    inspection_result_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("inspection_result.inspection_result_id", ondelete="SET NULL"),
        nullable=True,
    )

    memo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    product = relationship("Product")