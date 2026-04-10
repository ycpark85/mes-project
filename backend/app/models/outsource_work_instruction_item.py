from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class OutsourceWorkInstructionItem(Base):
    __tablename__ = "outsource_work_instruction_item"
    __table_args__ = (
        UniqueConstraint(
            "process_type",
            "lot_id",
            name="uq_outsource_work_instruction_item__process_type__lot_id",
        ),
        Index("ix_outsource_work_instruction_item__instruction_id", "outsource_work_instruction_id"),
        Index("ix_outsource_work_instruction_item__lot_id", "lot_id"),
    )

    outsource_work_instruction_item_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    outsource_work_instruction_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("outsource_work_instruction.outsource_work_instruction_id", ondelete="CASCADE"),
        nullable=False,
    )

    lot_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("lot.lot_id", ondelete="RESTRICT"),
        nullable=False,
    )

    process_type: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    instruction = relationship("OutsourceWorkInstruction", back_populates="items")
    lot = relationship("Lot")