from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
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
    - 일반 LOT: order_line 기준 1건 생성
    - 재작업 LOT: parent_lot_id 필수
    """

    order_line_id: int
    parent_lot_id: Optional[int] = None
    lot_qty: int = Field(..., gt=0)
    created_date: Optional[date] = None
    memo: Optional[str] = None

    material_lot_no: Optional[str] = None
    material_used_qty: Optional[Decimal] = Field(default=None, gt=0)
    material_sheet_count: Optional[int] = Field(default=None, gt=0)


class LotOut(BaseModel):
    lot_id: int
    lot_no: str
    order_line_id: int
    product_id: int
    parent_lot_id: Optional[int]

    lot_qty: int
    uom: str

    material_lot_no: Optional[str] = None
    material_used_qty: Optional[Decimal] = None
    material_sheet_count: Optional[int] = Field(default=None, gt=0)

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