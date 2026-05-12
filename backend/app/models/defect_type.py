from sqlalchemy import String, Boolean, Text, BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DefectType(Base):
    __tablename__ = "defect_type"

    defect_type_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    # 예: PRINT_BLUR
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)

    # 예: 인쇄
    category1_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)

    # 예: 인쇄번짐
    category2_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)

    # 불량 기준/설명/주의사항
    memo: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)