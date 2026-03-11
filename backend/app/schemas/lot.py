# app/schemas/lot.py
from __future__ import annotations

from datetime import date, datetime
from typing import Optional, List

from pydantic import BaseModel, Field


class LotStepOut(BaseModel):
    lot_step_id: int
    step_seq: int
    process_id: int
    process_code: str
    process_name: str
    process_type: str
    status: str
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class LotCreate(BaseModel):
    """
    - 일반 LOT: order_line 기준 1건 생성, lot_qty는 order_qty로 서버가 강제
    - 재작업 LOT: parent_lot_id 필수 + lot_qty는 사용자가 입력(확정 정책)
    """
    order_line_id: int
    parent_lot_id: Optional[int] = None # 재작업일 때 필수

    lot_qty: int = Field(..., gt=0)   
    created_date: Optional[date] = None
    memo: Optional[str] = None


class LotOut(BaseModel):
    lot_id: int
    lot_no: str

    order_line_id: int
    product_id: int
    parent_lot_id: Optional[int]

    lot_qty: int
    uom: str

    created_date: date
    due_date: date
    status: str 
    memo: Optional[str] = None

    created_at: datetime
    updated_at: datetime

    # 표시용(join)
    order_no: Optional[str] = None
    line_no: Optional[int] = None
    partner_id: Optional[int] = None
    partner_name: Optional[str] = None
    product_code: Optional[str] = None
    product_name: Optional[str] = None

    class Config:
        from_attributes = True


class LotDetailOut(LotOut):
    steps: List[LotStepOut] = []


class PageMeta(BaseModel):
    page: int
    size: int
    total: int


class LotListOut(BaseModel):
    items: List[LotOut]
    meta: PageMeta