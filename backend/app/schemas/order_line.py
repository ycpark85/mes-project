# app/schemas/order_line.py
from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, Field


class OrderLineStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    DONE = "DONE"
    CANCELED = "CANCELED"


class OrderLineBase(BaseModel):
    order_no: str = Field(..., max_length=40)
    line_no: int = Field(..., gt=0)

    partner_id: int
    product_id: int

    order_date: date
    due_date: date

    order_qty: int = Field(..., gt=0)
    uom: str = Field(..., max_length=10)

    customer_po: Optional[str] = Field(None, max_length=60)
    memo: Optional[str] = None


class OrderLineCreate(OrderLineBase):
    # status/is_active/priority는 서버 기본값 사용(입력 받지 않음)
    pass


class OrderLineUpdate(BaseModel):
    # OPEN일 때만 주요 필드 수정 허용 (검증은 router에서)
    order_no: Optional[str] = Field(None, max_length=40)
    line_no: Optional[int] = Field(None, gt=0)

    partner_id: Optional[int] = None
    product_id: Optional[int] = None

    order_date: Optional[date] = None
    due_date: Optional[date] = None

    order_qty: Optional[int] = Field(None, gt=0)
    uom: Optional[str] = Field(None, max_length=10)

    customer_po: Optional[str] = Field(None, max_length=60)
    memo: Optional[str] = None

    # 운영상 OPEN 이후에도 메모/PO는 변경 허용하고 싶으면 그대로 두고 router에서 허용 처리
    priority: Optional[int] = None  # 필요 시 허용 (기본은 OPEN에서만)


class OrderLineOut(OrderLineBase):
    order_line_id: int
    status: OrderLineStatus
    is_active: bool
    priority: int
    created_at: datetime
    updated_at: datetime

        # join으로 붙여주는 표시용 필드(조회 성능/UX)
    partner_name: Optional[str] = None
    product_code: Optional[str] = None
    product_name: Optional[str] = None

    # OrderLineList 액션 버튼 분기용
    has_lot: bool = False
    lot_count: int = 0

    class Config:
        from_attributes = True


class PageMeta(BaseModel):
    page: int
    size: int
    total: int


class OrderLineListOut(BaseModel):
    items: List[OrderLineOut]
    meta: PageMeta