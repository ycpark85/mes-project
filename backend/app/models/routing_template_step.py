from __future__ import annotations

from typing import TYPE_CHECKING
from sqlalchemy import String, Boolean, ForeignKey, UniqueConstraint, CheckConstraint,BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.routing_template import RoutingTemplate
    from app.models.process import Process

class RoutingTemplateStep(Base):
    __tablename__ = "routing_template_step"
    __table_args__ = (
        UniqueConstraint("routing_template_id", "step_seq", name="uq_routing_template_step_seq"),
        CheckConstraint("step_seq > 0", name="ck_routing_template_step_seq_gt_0"),
        CheckConstraint(
            "default_process_type IN ('OUTSOURCE','INTERNAL')",
            name="ck_routing_template_step_default_process_type",
        ),
    )

    routing_template_step_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    routing_template_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("routing_template.routing_template_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    step_seq: Mapped[int] = mapped_column(nullable=False)  # 10/20/30...
    process_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("process.process_id"),
        index=True,
        nullable=False,
    )

    default_process_type: Mapped[str] = mapped_column(String(20), nullable=False)  # OUTSOURCE/INTERNAL
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    template: Mapped[RoutingTemplate] = relationship(back_populates="steps")
    process: Mapped[Process] = relationship()