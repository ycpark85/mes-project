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

     # LOT 리스트 화면용
    order_date: Optional[date] = None
    order_qty: Optional[int] = None
    inspection_schedule_id: Optional[int] = None
    inspection_status: Optional[str] = None
    list_status: Optional[str] = None
    list_status_display: Optional[str] = None
    lot_type: Optional[str] = None
    lot_type_display: Optional[str] = None
    
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

# lot상세 정보조회 DTO

class LotTraceProgressOut(BaseModel):
    lot_created: bool = True
    outsource_instruction_created: bool = False
    outsource_work_done: bool = False
    inspection_done: bool = False


class LotTraceBasicOut(BaseModel):
    lot_id: int
    lot_no: str
    status: str
    is_rework: bool
    parent_lot_id: Optional[int] = None
    parent_lot_no: Optional[str] = None
    lot_qty: int
    uom: str
    created_date: date
    due_date: date
    memo: Optional[str] = None


class LotTraceProductOrderOut(BaseModel):
    order_line_id: int
    order_no: str
    line_no: int
    partner_id: int
    partner_name: Optional[str] = None
    product_id: int
    product_code: str
    product_name: str
    product_spec: Optional[str] = None
    panel_width_mm: Optional[int] = None
    panel_length_mm: Optional[int] = None
    cut_qty_per_panel: Optional[int] = None
    order_qty: int
    order_date: date
    due_date: date


class LotTraceOutsourceWorkOut(BaseModel):
    outsource_work_group_id: int
    outsource_work_group_item_id: int
    outsource_work_instruction_id: int
    instruction_no: str
    instruction_date: date
    process_type: str
    group_seq: str
    is_bundle: bool
    fabric_lot_no: Optional[str] = None
    length_m: Optional[Decimal] = None
    sheet_qty: int
    sheet_cut_count: int
    cuts_per_sheet: int
    expected_output_qty: Optional[int] = None
    group_expected_output_qty: int
    work_done_sheet_qty: Optional[int] = None
    confirmed_outsource_qty: Optional[int] = None
    status: Optional[str] = None
    vendor_received_at: Optional[datetime] = None
    work_done_at: Optional[datetime] = None
    shipped_at: Optional[datetime] = None
    remark: Optional[str] = None
    work_done_remark: Optional[str] = None


class LotTraceInspectionDefectOut(BaseModel):
    inspection_defect_id: int
    defect_type_id: int
    defect_type_code: Optional[str] = None
    defect_type_name: Optional[str] = None
    defect_qty: int
    disposition: str
    memo: Optional[str] = None


class LotTraceInspectionOut(BaseModel):
    inspection_schedule_id: Optional[int] = None
    inspection_date: Optional[date] = None
    schedule_status: Optional[str] = None
    received_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    inspection_result_id: Optional[int] = None
    inspected_qty: Optional[int] = None
    good_qty: Optional[int] = None
    defect_qty: Optional[int] = None
    defect_ship_qty: Optional[int] = None
    is_partial: Optional[bool] = None
    next_inspection_date: Optional[date] = None
    partial_reason: Optional[str] = None
    created_by: Optional[str] = None
    result_created_at: Optional[datetime] = None

    defects: List[LotTraceInspectionDefectOut] = Field(default_factory=list)


class LotTraceDetailOut(BaseModel):
    progress: LotTraceProgressOut
    lot_basic: LotTraceBasicOut
    product_order: LotTraceProductOrderOut
    outsource_works: List[LotTraceOutsourceWorkOut] = Field(default_factory=list)
    inspection: Optional[LotTraceInspectionOut] = None