from __future__ import annotations

from datetime import date, datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

Disposition = Literal["SHIP_AS_IS", "NOT_SHIPPABLE"]


class DefectAttachmentIn(BaseModel):
    file_uri: str = Field(..., min_length=1, max_length=600)
    file_name: Optional[str] = Field(default=None, max_length=255)
    mime_type: Optional[str] = Field(default=None, max_length=100)
    memo: Optional[str] = None


class DefectLineIn(BaseModel):
    defect_type_id: int = Field(..., ge=1)
    defect_qty: int = Field(..., ge=0)
    disposition: Disposition = "NOT_SHIPPABLE"
    memo: Optional[str] = None
    attachments: List[DefectAttachmentIn] = Field(default_factory=list)


class InspectionResultUpsertIn(BaseModel):
    good_qty: int = Field(..., ge=0)
    defect_ship_qty: int = Field(0, ge=0)
    defect_qty: int = Field(..., ge=0)

    stock_ship_qty: int = Field(0, ge=0)
    result_ship_qty: int = Field(0, ge=0)
    stock_in_qty: int = Field(0, ge=0)

    is_partial: bool = False
    next_inspection_date: Optional[date] = None
    partial_reason: Optional[str] = None
    memo: Optional[str] = None

    defects: List[DefectLineIn] = Field(default_factory=list)


class DefectAttachmentUploadOut(BaseModel):
    file_uri: str
    file_name: str
    mime_type: Optional[str] = None
    file_size: int


class DefectAttachmentOut(BaseModel):
    inspection_defect_attachment_id: int
    file_uri: str
    file_name: Optional[str] = None
    mime_type: Optional[str] = None
    memo: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DefectLineOut(BaseModel):
    inspection_defect_id: int
    defect_type_id: int
    defect_qty: int
    disposition: str
    memo: Optional[str] = None
    created_at: datetime
    attachments: List[DefectAttachmentOut] = Field(default_factory=list)

    class Config:
        from_attributes = True


class InspectionResultOut(BaseModel):
    inspection_result_id: int
    inspection_schedule_id: int
    good_qty: int
    defect_ship_qty: int
    defect_qty: int
    inspected_qty: int

    is_partial: bool
    next_inspection_date: Optional[date] = None
    partial_reason: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    defects: List[DefectLineOut] = Field(default_factory=list)

    class Config:
        from_attributes = True


class InspectionAccumulatedSummaryOut(BaseModel):
    good_qty: int = 0
    defect_qty: int = 0
    defect_ship_qty: int = 0
    inspected_qty: int = 0


class InspectionInventorySummaryOut(BaseModel):
    product_id: int
    order_line_id: int

    current_stock_qty: int = 0
    order_qty: int = 0
    ship_target_qty: int = 0
    already_shipped_qty: int = 0
    remaining_ship_target_qty: int = 0

    current_result_stock_ship_qty: int = 0
    current_result_result_ship_qty: int = 0
    current_result_stock_in_qty: int = 0


class InspectionResultGetOut(BaseModel):
    result: Optional[InspectionResultOut] = None
    accumulated: InspectionAccumulatedSummaryOut = Field(default_factory=InspectionAccumulatedSummaryOut)
    inventory: InspectionInventorySummaryOut | None = None


class InspectionResultUpsertOut(BaseModel):
    result: InspectionResultOut
    schedule_status: str
    created_next_schedule_id: Optional[int] = None