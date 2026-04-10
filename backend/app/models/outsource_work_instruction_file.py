from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class OutsourceWorkInstructionFile(Base):
    __tablename__ = "outsource_work_instruction_file"
    __table_args__ = (
        Index("ix_outsource_work_instruction_file__instruction_id", "outsource_work_instruction_id"),
    )

    outsource_work_instruction_file_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    outsource_work_instruction_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("outsource_work_instruction.outsource_work_instruction_id", ondelete="CASCADE"),
        nullable=False,
    )

    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    instruction = relationship("OutsourceWorkInstruction", back_populates="files")