# app/schemas/inspection_schedule.py
from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class InspectionScheduleCreate(BaseModel):
    lot_id: int = Field(..., ge=1)
    inspection_date: date
    memo: Optional[str] = None


class InspectionScheduleOut(BaseModel):
    inspection_schedule_id: int
    lot_id: int
    inspection_date: date
    status: str
    day_seq: Optional[int] = None

    received_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    memo: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class InspectionScheduleUpdate(BaseModel):
    inspection_date: Optional[date] = None
    memo: Optional[str] = None


class InspectionScheduleReorderIn(BaseModel):
    inspection_date: date
    ordered_ids: List[int] = Field(..., min_length=1)


class InspectionScheduleListItemOut(BaseModel):
    inspection_schedule_id: int
    lot_id: int
    lot_no: str

    inspection_date: date
    status: str
    day_seq: Optional[int] = None

    due_date: date
    partner_name: str
    product_code: str
    product_name: str
    lot_qty: int
    order_qty: int
    ship_qty: int
    memo: Optional[str] = None

    class Config:
        from_attributes = False