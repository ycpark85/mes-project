from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Index, String, Text, CheckConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from decimal import Decimal


class OutsourceWorkInstruction(Base):
    __tablename__ = "outsource_work_instruction"
    __table_args__ = (
        CheckConstraint(
            "process_type IN ('CUT','PRINT')",
            name="ck_outsource_work_instruction__process_type",
        ),
        Index("ix_outsource_work_instruction__instruction_date", "instruction_date"),
        Index("ix_outsource_work_instruction__process_type", "process_type"),
        Index("ix_outsource_work_instruction__partner_id", "partner_id"),
    )

    outsource_work_instruction_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    instruction_no: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    instruction_date: Mapped[date] = mapped_column(Date, nullable=False)

    process_type: Mapped[str] = mapped_column(String(20), nullable=False)
    partner_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("partner.partner_id", ondelete="RESTRICT"),
        nullable=False,
    )

    is_bundle: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    memo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    partner = relationship("Partner")
    items: Mapped[List["OutsourceWorkInstructionItem"]] = relationship(
    "OutsourceWorkInstructionItem",
    back_populates="instruction",
    cascade="all, delete-orphan",
    )

    files: Mapped[List["OutsourceWorkInstructionFile"]] = relationship(
        "OutsourceWorkInstructionFile",
        back_populates="instruction",
        cascade="all, delete-orphan",
    )

