# app/models/inspection_schedule.py
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    String,
    Text,
    Index,
    CheckConstraint,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class InspectionSchedule(Base):
    """
    검수 스케줄(회차) – SSOT v1
    - LOT 기준 검수 실행 단위
    - 수량 정보 없음 (실적에서만 관리)
    """

    __tablename__ = "inspection_schedule"
    __table_args__ = (
        UniqueConstraint(
            "lot_id",
            "inspection_date",
            name="uq_inspection_schedule__lot__date",
        ),
        CheckConstraint(
            "status IN ('WAITING','RECEIVED','IN_PROGRESS','PARTIAL_DONE','DONE','CANCELED')",
            name="ck_inspection_schedule__status",
        ),
        Index("ix_inspection_schedule__inspection_date", "inspection_date"),
        Index("ix_inspection_schedule__lot_id", "lot_id"),
        Index("ix_inspection_schedule__outsource_work_group_id", "outsource_work_group_id"),
        Index("ix_inspection_schedule__outsource_work_group_item_id", "outsource_work_group_item_id"),
    )

    inspection_schedule_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    lot_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("lot.lot_id", ondelete="CASCADE"),
        nullable=False,
    )
    outsource_work_group_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey(
            "outsource_work_group.outsource_work_group_id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    outsource_work_group_item_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey(
            "outsource_work_group_item.outsource_work_group_item_id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )   

    inspection_date: Mapped[date] = mapped_column(Date, nullable=False)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="WAITING")

    # 화면 표시용 (일자 내 순서)
    day_seq: Mapped[Optional[int]] = mapped_column(nullable=True)

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    memo: Mapped[Optional[str]] = mapped_column(Text)

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
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    lot = relationship("Lot")
    outsource_work_group = relationship("OutsourceWorkGroup")
    outsource_work_group_item = relationship("OutsourceWorkGroupItem")