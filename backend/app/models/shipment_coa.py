from __future__ import annotations

from datetime import date, datetime
from typing import Optional
from sqlalchemy import Boolean

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ShipmentCoa(Base):
    """
    출고 COA 스냅샷

    - 출고완료 주문라인(order_line_id) 기준 1건
    - 기본값은 shipment_line / order_line / product / partner / lot 기준으로 생성
    - 업체 요청 시 검사일자, 수량만 수정 허용
    """

    __tablename__ = "shipment_coa"
    __table_args__ = (
        UniqueConstraint("order_line_id", name="uq_shipment_coa__order_line"),
        CheckConstraint("quantity_snapshot >= 0", name="ck_shipment_coa__quantity_snapshot"),
        Index("ix_shipment_coa__order_line_id", "order_line_id"),
        Index("ix_shipment_coa__product_id", "product_id"),
        Index("ix_shipment_coa__issued_at", "issued_at"),
    )

    shipment_coa_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

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

    product_name_snapshot: Mapped[str] = mapped_column(String(200), nullable=False)
    product_spec_snapshot: Mapped[str] = mapped_column(String(100), nullable=False)
    material_snapshot: Mapped[str] = mapped_column(String(100), nullable=False)
    partner_name_snapshot: Mapped[str] = mapped_column(String(200), nullable=False)

    lot_nos_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    stock_lot_nos_snapshot: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    production_lot_nos_snapshot: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    quantity_snapshot: Mapped[int] = mapped_column(BigInteger, nullable=False)
    inspection_date_snapshot: Mapped[date] = mapped_column(Date, nullable=False)

    issued_at: Mapped[datetime] = mapped_column(
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

    memo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    order_line = relationship("OrderLine")
    product = relationship("Product")


    is_printed_product_snapshot: Mapped[Optional[bool]] = mapped_column(
        Boolean,
        nullable=True,
    )