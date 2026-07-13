from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, String, Text, false, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class VendorPortalAuditLog(Base):
    __tablename__ = "vendor_portal_audit_log"

    __table_args__ = (
        Index("ix_vendor_portal_audit_log__user_id", "user_id"),
        Index("ix_vendor_portal_audit_log__partner_id", "partner_id"),
        Index("ix_vendor_portal_audit_log__work_group_id", "outsource_work_group_id"),
        Index("ix_vendor_portal_audit_log__action_type", "action_type"),
        Index("ix_vendor_portal_audit_log__created_at", "created_at"),
    )

    vendor_portal_audit_log_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )

    user_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
    )

    partner_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("partner.partner_id", ondelete="SET NULL"),
        nullable=True,
    )

    outsource_work_group_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("outsource_work_group.outsource_work_group_id", ondelete="SET NULL"),
        nullable=True,
    )

    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    before_status: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    after_status: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    request_ip: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    user_agent_truncated: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
