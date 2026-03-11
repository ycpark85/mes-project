# app/models/lot_step.py
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger, DateTime, ForeignKey, Integer, String,
    CheckConstraint, Index, UniqueConstraint, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class LotStep(Base):
    __tablename__ = "lot_step"
    __table_args__ = (
        UniqueConstraint("lot_id", "step_seq", name="uq_lot_step__lot_id__step_seq"),
        CheckConstraint("step_seq > 0", name="ck_lot_step__step_seq_gt_0"),
        CheckConstraint(
            "status IN ('WAITING','IN_PROGRESS','DONE','CANCELED')",
            name="ck_lot_step__status_enum",
        ),
        Index("ix_lot_step__lot_id", "lot_id"),
        Index("ix_lot_step__process_id", "process_id"),
    )

    lot_step_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    lot_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("lot.lot_id", ondelete="CASCADE"),
        nullable=False,
    )

    # 라우팅 스냅샷
    step_seq: Mapped[int] = mapped_column(Integer, nullable=False)
    process_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("process.process_id", ondelete="RESTRICT"),
        nullable=False,
    )

    # 조회 편의(스냅샷) - 선택이지만 실무에선 유용
    process_code: Mapped[str] = mapped_column(String(30), nullable=False)
    process_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # OUTSOURCE / INTERNAL (routing_template_step의 default_process_type 스냅샷)
    process_type: Mapped[str] = mapped_column(String(20), nullable=False)

    # 상태 SSOT
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="WAITING")
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    lot = relationship("Lot", back_populates="steps")
    process = relationship("Process")