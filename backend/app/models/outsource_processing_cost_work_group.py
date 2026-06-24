from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class OutsourceProcessingCostWorkGroup(Base):
    __tablename__ = "outsource_processing_cost_work_group"
    __table_args__ = (
        UniqueConstraint(
            "outsource_processing_cost_group_id",
            "outsource_work_group_id",
            name="uq_outsource_processing_cost_work_group__group_work_group",
        ),
        Index(
            "ix_outsource_processing_cost_work_group__cost_group_id",
            "outsource_processing_cost_group_id",
        ),
        Index(
            "ix_outsource_processing_cost_work_group__work_group_id",
            "outsource_work_group_id",
        ),
    )

    outsource_processing_cost_work_group_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )
    outsource_processing_cost_group_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "outsource_processing_cost_group.outsource_processing_cost_group_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    outsource_work_group_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("outsource_work_group.outsource_work_group_id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    cost_group = relationship(
        "OutsourceProcessingCostGroup",
        back_populates="work_groups",
    )
    work_group = relationship("OutsourceWorkGroup")
