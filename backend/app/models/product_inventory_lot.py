from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ProductInventoryLot(Base):
    __tablename__ = "product_inventory_lot"
    __table_args__ = (
        UniqueConstraint("product_id", "lot_no", name="uq_product_inventory_lot__product_id__lot_no"),
        Index("ix_product_inventory_lot__product_id", "product_id"),
        Index("ix_product_inventory_lot__lot_no", "lot_no"),
    )

    product_inventory_lot_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    product_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("product.product_id", ondelete="RESTRICT"),
        nullable=False,
    )

    lot_no: Mapped[str] = mapped_column(String(100), nullable=False)
    current_qty: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

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

    product = relationship("Product")
