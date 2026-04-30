# app/schemas/inspection_schedule.py
from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class InspectionScheduleCreate(BaseModel):
    lot_id: int = Field(..., ge=1)
    inspection_date: date
    memo: Optional[str] = None

    outsource_work_group_id: Optional[int] = Field(default=None, ge=1)
    outsource_work_group_item_id: Optional[int] = Field(default=None, ge=1)


class InspectionScheduleOut(BaseModel):
    inspection_schedule_id: int
    lot_id: int
    outsource_work_group_id: Optional[int] = None
    outsource_work_group_item_id: Optional[int] = None
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
    outsource_work_group_id: Optional[int] = None
    outsource_work_group_item_id: Optional[int] = None
    bundle_no: Optional[str] = None
    diecut_status: Optional[str] = None
    
    drawing_id: Optional[int] = None
    drawing_no: Optional[str] = None

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

class InspectionWorkInstructionTargetOut(BaseModel):
    lot_id: int
    lot_no: str

    outsource_work_group_id: Optional[int] = None
    outsource_work_group_item_id: Optional[int] = None
    bundle_no: Optional[str] = None

    product_code: Optional[str] = None
    product_name: Optional[str] = None
    partner_name: Optional[str] = None

    lot_qty: int
    due_date: Optional[date] = None
    memo: Optional[str] = None


class InspectionWorkInstructionTargetListOut(BaseModel):
    items: List[InspectionWorkInstructionTargetOut] = Field(default_factory=list)        