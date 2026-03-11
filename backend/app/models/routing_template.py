from __future__ import annotations

from typing import TYPE_CHECKING
from sqlalchemy import String, Boolean,BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.routing_template_step import RoutingTemplateStep

class RoutingTemplate(Base):
    __tablename__ = "routing_template"

    routing_template_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    template_code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    template_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    steps: Mapped[list[RoutingTemplateStep]] = relationship(
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="RoutingTemplateStep.step_seq",
    )