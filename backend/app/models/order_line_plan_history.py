from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class OrderLinePlanHistory(Base):
    __tablename__ = "order_line_plan_history"

    plan_history_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    order_line_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("order_line.order_line_id", ondelete="CASCADE"),
        nullable=False,
    )

    plan_type: Mapped[str] = mapped_column(String(40), nullable=False)

    ship_target_qty: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    available_inventory_qty: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stock_ship_qty: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    production_qty: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    is_short_close: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    memo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    order_line = relationship("OrderLine")


Index(
    "ix_order_line_plan_history__order_line_latest",
    OrderLinePlanHistory.order_line_id,
    OrderLinePlanHistory.created_at.desc(),
    OrderLinePlanHistory.plan_history_id.desc(),
)
