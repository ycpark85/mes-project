from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class VendorUserAccess(Base):
    __tablename__ = "vendor_user_access"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "partner_id",
            name="uq_vendor_user_access__user_partner",
        ),
        Index("ix_vendor_user_access__user_id", "user_id"),
        Index("ix_vendor_user_access__partner_id", "partner_id"),
        Index("ix_vendor_user_access__is_active", "is_active"),
    )

    vendor_user_access_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )

    partner_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("partner.partner_id", ondelete="RESTRICT"),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

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

