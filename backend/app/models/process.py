# app/models/process.py
from sqlalchemy import String, Boolean,BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

class Process(Base):
    __tablename__ = "process"

    process_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    process_code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    process_name: Mapped[str] = mapped_column(String(200), nullable=False)

    # outsource / internal
    process_type: Mapped[str] = mapped_column(String(20), nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)