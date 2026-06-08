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


class ShipmentLine(Base):
    __tablename__ = "shipment_line"

    __table_args__ = (
        CheckConstraint(
            "status IN ('WAITING','DONE','CANCELED')",
            name="ck_shipment_line__status",
        ),
        CheckConstraint(
            "source_type IN ('STOCK','INSPECTION_RESULT')",
            name="ck_shipment_line__source_type",
        ),
        CheckConstraint(
            "ship_qty >= 0",
            name="ck_shipment_line__ship_qty",
        ),
        CheckConstraint(
            "shipped_qty >= 0",
            name="ck_shipment_line__shipped_qty",
        ),
        Index("ix_shipment_line__order_line_id", "order_line_id"),
        Index("ix_shipment_line__product_id", "product_id"),
        Index("ix_shipment_line__lot_id", "lot_id"),
        Index("ix_shipment_line__product_inventory_lot_id", "product_inventory_lot_id"),
        Index("ix_shipment_line__stock_lot_no", "stock_lot_no"),
        Index("ix_shipment_line__inspection_result_id", "inspection_result_id"),
        Index("ix_shipment_line__status", "status"),
        Index("ix_shipment_line__created_at", "created_at"),
        Index("ix_shipment_line__status_created", "status", "created_at", "shipment_line_id"),
        Index(
            "ix_shipment_line__inventory_lot_source_status",
            "product_inventory_lot_id",
            "source_type",
            "status",
        ),
        Index(
            "ix_shipment_line__order_line_source_status_result",
            "order_line_id",
            "source_type",
            "status",
            "inspection_result_id",
        ),
    )

    shipment_line_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    order_line_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("order_line.order_line_id", ondelete="RESTRICT"),
        nullable=False,
    )

    product_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("product.product_id", ondelete="RESTRICT"),
        nullable=False,
    )

    product_inventory_lot_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("product_inventory_lot.product_inventory_lot_id", ondelete="SET NULL"),
        nullable=True,
    )

    stock_lot_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    lot_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("lot.lot_id", ondelete="SET NULL"),
        nullable=True,
    )

    inspection_result_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("inspection_result.inspection_result_id", ondelete="SET NULL"),
        nullable=True,
    )

    source_type: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="WAITING")

    ship_qty: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    shipped_qty: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    memo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    shipped_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    order_line = relationship("OrderLine")
    product = relationship("Product")
    inventory_lot = relationship("ProductInventoryLot")
    lot = relationship("Lot")
    inspection_result = relationship("InspectionResult")
