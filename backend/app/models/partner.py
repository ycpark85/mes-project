from sqlalchemy import String, Boolean,BigInteger
from sqlalchemy.orm import Mapped, mapped_column,relationship
from typing import List
from app.db.base import Base


class Partner(Base):
    __tablename__ = "partner"

    partner_id: Mapped[int] = mapped_column(BigInteger,primary_key=True)

    # CUSTOMER / VENDOR
    partner_type: Mapped[str] = mapped_column(String(20), nullable=False)

    name: Mapped[str] = mapped_column(
    String(200),
    nullable=False,
    index=True,
    )

    # ✅ 사업자등록번호 (하이픈 포함/미포함 모두 수용)
    business_no: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    order_lines: Mapped[List["OrderLine"]] = relationship("OrderLine", back_populates="partner")