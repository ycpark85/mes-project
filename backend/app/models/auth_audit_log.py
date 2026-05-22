from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuthAuditLog(Base):
    __tablename__ = "auth_audit_logs"

    __table_args__ = (
        Index("ix_auth_audit_logs__event_type", "event_type"),
        Index("ix_auth_audit_logs__login_id", "login_id"),
        Index("ix_auth_audit_logs__user_id", "user_id"),
        Index("ix_auth_audit_logs__success", "success"),
        Index("ix_auth_audit_logs__created_at", "created_at"),
    )

    auth_audit_log_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    login_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
    )

    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    client_ip: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )