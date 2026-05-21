from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Permission(Base):
    __tablename__ = "permissions"

    __table_args__ = (
        Index("ix_permissions__permission_code", "permission_code"),
        Index("ix_permissions__menu_code", "menu_code"),
        Index("ix_permissions__action_code", "action_code"),
        Index("ix_permissions__is_active", "is_active"),
    )

    permission_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    permission_code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    menu_code: Mapped[str] = mapped_column(String(50), nullable=False)
    action_code: Mapped[str] = mapped_column(String(50), nullable=False)

    permission_name: Mapped[str] = mapped_column(String(200), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

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

    role_permissions = relationship(
        "RolePermission",
        back_populates="permission",
        cascade="all, delete-orphan",
    )
    