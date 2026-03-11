# app/models/lot.py
from __future__ import annotations

from datetime import date, datetime
from typing import Optional, List

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Index,
    CheckConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Lot(Base):
    """
    LOT = 생산/검수/출하 기준 단위 (MVP)
    - order_line 기준으로 생성
    - 재작업: parent_lot_id
    - 수량 SSOT(증산/감산 반영): lot_qty + uom
    - 공정상태 SSOT는 lot_step (lot 상태는 lot_step 집계로 전이)
    """

    __tablename__ = "lot"
    __table_args__ = (
        CheckConstraint("lot_qty > 0", name="ck_lot__lot_qty_gt_0"),
        Index("ix_lot__order_line_id", "order_line_id"),
        Index("ix_lot__product_id", "product_id"),
        Index("ix_lot__created_date", "created_date"),
        Index("ix_lot__lot_no", "lot_no"),
        Index("ix_lot__due_date", "due_date"), 
    )

    lot_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    # ✅ lot_no: CT + YY + M + DD + E + NN (서비스에서 생성)
    lot_no: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)

    # SSOT 참조
    order_line_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("order_line.order_line_id", ondelete="RESTRICT"),
        nullable=False,
    )

    # 조회 최적화/스냅샷 성격
    product_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("product.product_id", ondelete="RESTRICT"),
        nullable=False,
    )

    # 재작업 (부모 LOT)
    parent_lot_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("lot.lot_id", ondelete="SET NULL"),
        nullable=True,
    )

    # LOT 수량/단위 (order_line에서 복사 후 LOT 기준으로 확정)
    lot_qty: Mapped[int] = mapped_column(BigInteger, nullable=False)
    uom: Mapped[str] = mapped_column(String(10), nullable=False)

    # 업무 기준 생성일
    created_date: Mapped[date] = mapped_column(Date, nullable=False)

    memo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="WAITING")

    # 관계
    order_line = relationship("OrderLine", back_populates="lots")
    product = relationship("Product")
    parent_lot = relationship("Lot", remote_side="Lot.lot_id")

    steps: Mapped[List["LotStep"]] = relationship(
        "LotStep",
        back_populates="lot",
        cascade="all, delete-orphan",
        order_by="LotStep.step_seq",
    )
     #✅ OrderLine 납기 스냅샷
    due_date: Mapped[date] = mapped_column(Date, nullable=False)  # ✅ 추가