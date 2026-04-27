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
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class OutsourceWorkGroupItem(Base):
    __tablename__ = "outsource_work_group_item"
    __table_args__ = (
        CheckConstraint(
            "cuts_per_sheet > 0",
            name="ck_outsource_work_group_item__cuts_per_sheet_gt_0",
        ),
        CheckConstraint(
            "expected_output_qty IS NULL OR expected_output_qty >= 0",
            name="ck_outsource_work_group_item__expected_output_qty_ge_0",
        ),
        CheckConstraint(
            "actual_output_qty IS NULL OR actual_output_qty >= 0",
            name="ck_outsource_work_group_item__actual_output_qty_ge_0",
        ),
        Index(
            "ix_outsource_work_group_item__work_group_id",
            "outsource_work_group_id",
        ),
        Index(
            "ix_outsource_work_group_item__lot_id",
            "lot_id",
        ),
    )

    outsource_work_group_item_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )

    outsource_work_group_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "outsource_work_group.outsource_work_group_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    lot_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("lot.lot_id", ondelete="RESTRICT"),
        nullable=False,
    )

    cuts_per_sheet: Mapped[int] = mapped_column(Integer, nullable=False)
    expected_output_qty: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    actual_output_qty: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    work_group = relationship(
        "OutsourceWorkGroup",
        back_populates="items",
    )

    lot = relationship("Lot")