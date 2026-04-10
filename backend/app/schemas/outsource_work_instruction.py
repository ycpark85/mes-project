from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class OutsourceWorkInstructionFileCreate(BaseModel):
    file_name: str = Field(..., min_length=1, max_length=255)
    file_path: str = Field(..., min_length=1)
    content_type: Optional[str] = None


class OutsourceWorkInstructionCreate(BaseModel):
    instruction_date: date
    process_type: str
    partner_id: int
    lot_ids: List[int] = Field(..., min_length=1)
    memo: Optional[str] = None
    files: List[OutsourceWorkInstructionFileCreate] = Field(default_factory=list)

class OutsourceWorkInstructionFileOut(BaseModel):
    outsource_work_instruction_file_id: int
    file_name: str
    file_path: str
    content_type: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class OutsourceWorkInstructionItemOut(BaseModel):
    outsource_work_instruction_item_id: int
    lot_id: int
    lot_no: Optional[str] = None
    order_no: Optional[str] = None
    line_no: Optional[int] = None
    product_code: Optional[str] = None
    product_name: Optional[str] = None
    lot_qty: Optional[int] = None
    process_type: str

    class Config:
        from_attributes = True


class OutsourceWorkInstructionOut(BaseModel):
    outsource_work_instruction_id: int
    instruction_no: str
    instruction_date: date
    process_type: str
    partner_id: int
    is_bundle: bool
    memo: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    items: List[OutsourceWorkInstructionItemOut] = []
    files: List[OutsourceWorkInstructionFileOut] = []

    class Config:
        from_attributes = True


class OutsourceWorkInstructionCandidateLotOut(BaseModel):
    lot_id: int
    lot_no: str
    order_line_id: int
    order_no: str
    line_no: int
    product_id: int
    product_code: str
    product_name: str
    partner_id: int
    partner_name: Optional[str] = None
    lot_qty: int
    available_process_types: List[str]

class OutsourceWorkInstructionPlateUploadOut(BaseModel):
    file_name: str
    file_path: str
    content_type: Optional[str] = None
    file_size: int
    uploaded_at: datetime


class OutsourceWorkInstructionCandidateLotListOut(BaseModel):
    items: List[OutsourceWorkInstructionCandidateLotOut]