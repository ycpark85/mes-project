from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, model_validator


PURPOSE_TYPES = {"PRINT_SETUP", "SAMPLE", "TEST_RND", "OTHER"}
EXECUTION_TYPES = {"INTERNAL", "OUTSOURCE"}


class SelfUseSheetAllocationCreate(BaseModel):
    raw_material_inventory_lot_id: int = Field(..., ge=1)
    planned_qty: Decimal = Field(..., gt=0)


class SelfUseSheetJobCreate(BaseModel):
    purpose_type: str = Field(..., min_length=1, max_length=30)
    execution_type: str = Field(..., min_length=1, max_length=20)
    partner_id: Optional[int] = Field(default=None, ge=1)
    cut_width_mm: Decimal = Field(..., gt=0)
    cut_length_mm: Decimal = Field(..., gt=0)
    planned_output_qty: int = Field(..., gt=0)
    expected_processing_fee: Decimal = Field(default=Decimal("0"), ge=0)
    memo: Optional[str] = None
    allocations: list[SelfUseSheetAllocationCreate] = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_business_fields(self):
        self.purpose_type = self.purpose_type.strip().upper()
        self.execution_type = self.execution_type.strip().upper()
        if self.purpose_type not in PURPOSE_TYPES:
            raise ValueError("Invalid purpose_type")
        if self.execution_type not in EXECUTION_TYPES:
            raise ValueError("Invalid execution_type")
        if self.execution_type == "OUTSOURCE" and self.partner_id is None:
            raise ValueError("partner_id is required for outsource work")
        if self.purpose_type == "OTHER" and not (self.memo or "").strip():
            raise ValueError("memo is required for OTHER purpose")
        return self


class SelfUseSheetJobStart(BaseModel):
    expected_version: int = Field(..., ge=1)


class SelfUseSheetAllocationComplete(BaseModel):
    allocation_id: int = Field(..., ge=1)
    actual_consumed_qty: Decimal = Field(..., gt=0)
    returned_qty: Decimal = Field(default=Decimal("0"), ge=0)


class SelfUseSheetJobComplete(BaseModel):
    expected_version: int = Field(..., ge=1)
    produced_qty: int = Field(..., gt=0)
    scrap_qty: int = Field(default=0, ge=0)
    actual_processing_fee: Decimal = Field(default=Decimal("0"), ge=0)
    memo: Optional[str] = None
    allocations: list[SelfUseSheetAllocationComplete] = Field(..., min_length=1)


class SelfUseSheetJobCancel(BaseModel):
    expected_version: int = Field(..., ge=1)
    reason: str = Field(..., min_length=1)


class SelfUseSheetAllocationOut(BaseModel):
    self_use_sheet_raw_material_allocation_id: int
    raw_material_id: int
    material_code: str
    material_name: str
    uom: str
    source_location_id: int
    source_location_name: str
    original_inventory_lot_id: Optional[int] = None
    processing_inventory_lot_id: Optional[int] = None
    lot_no: str
    planned_qty: Decimal
    actual_consumed_qty: Optional[Decimal] = None
    returned_qty: Decimal
    unit_cost_snapshot: Optional[Decimal] = None
    amount_snapshot: Optional[Decimal] = None
    status: str


class SelfUseSheetJobOut(BaseModel):
    self_use_sheet_job_id: int
    use_no: str
    purpose_type: str
    execution_type: str
    partner_id: Optional[int] = None
    partner_name: Optional[str] = None
    status: str
    cut_width_mm: Decimal
    cut_length_mm: Decimal
    planned_output_qty: int
    expected_processing_fee: Decimal
    actual_processing_fee: Optional[Decimal] = None
    actual_input_qty: Optional[Decimal] = None
    produced_qty: Optional[int] = None
    scrap_qty: Optional[int] = None
    memo: Optional[str] = None
    cancel_reason: Optional[str] = None
    created_by: str
    started_by: Optional[str] = None
    completed_by: Optional[str] = None
    canceled_by: Optional[str] = None
    version: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    canceled_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    sheet_lot_id: Optional[int] = None
    sheet_lot_no: Optional[str] = None
    allocations: list[SelfUseSheetAllocationOut]


class SelfUseSheetJobListOut(BaseModel):
    items: list[SelfUseSheetJobOut]
    total: int
    page: int
    size: int


class SelfUseSheetInventoryLotOut(BaseModel):
    self_use_sheet_inventory_lot_id: int
    self_use_sheet_job_id: int
    use_no: str
    purpose_type: str
    execution_type: str
    partner_name: Optional[str] = None
    raw_material_id: int
    material_code: str
    material_name: str
    sheet_lot_no: str
    source_lot_summary: str
    cut_width_mm: Decimal
    cut_length_mm: Decimal
    initial_qty: int
    used_qty: int
    current_qty: int
    material_amount: Decimal
    processing_fee: Decimal
    total_cost: Decimal
    unit_cost: Decimal
    status: str
    version: int
    completed_at: datetime
    updated_at: datetime
    locations: list["SelfUseSheetInventoryLocationOut"] = Field(default_factory=list)
    source_lots: list["SelfUseSheetSourceLotOut"] = Field(default_factory=list)


class SelfUseSheetInventoryLocationOut(BaseModel):
    raw_material_location_id: int
    location_code: str
    location_name: str
    location_type: str
    current_qty: int


class SelfUseSheetSourceLotOut(BaseModel):
    raw_material_inventory_lot_id: Optional[int] = None
    raw_material_id: int
    material_code: str
    material_name: str
    source_location_id: int
    source_location_name: str
    lot_no: str
    actual_consumed_qty: Decimal
    unit_cost_snapshot: Decimal
    amount_snapshot: Decimal


class SelfUseSheetInventorySummaryOut(BaseModel):
    lot_count: int
    initial_qty: int
    used_qty: int
    current_qty: int
    inventory_amount: Decimal


class SelfUseSheetInventoryLotListOut(BaseModel):
    items: list[SelfUseSheetInventoryLotOut]
    total: int
    page: int
    size: int
    summary: SelfUseSheetInventorySummaryOut


class SelfUseSheetUseIn(BaseModel):
    expected_version: int = Field(..., ge=1)
    purpose_type: str = Field(..., min_length=1, max_length=30)
    qty: int = Field(..., gt=0)
    raw_material_location_id: Optional[int] = Field(default=None, ge=1)
    memo: Optional[str] = None

    @model_validator(mode="after")
    def validate_usage(self):
        self.purpose_type = self.purpose_type.strip().upper()
        if self.purpose_type not in PURPOSE_TYPES:
            raise ValueError("Invalid purpose_type")
        if self.purpose_type == "OTHER" and not (self.memo or "").strip():
            raise ValueError("memo is required for OTHER purpose")
        return self


class SelfUseSheetUseReverseIn(BaseModel):
    expected_version: int = Field(..., ge=1)
    reason: str = Field(..., min_length=1)


class SelfUseSheetMovementOut(BaseModel):
    self_use_sheet_inventory_movement_id: int
    self_use_sheet_inventory_lot_id: int
    inventory_lot_version: int
    sheet_lot_no: str
    material_name: str
    movement_type: str
    raw_material_location_id: int
    location_name: str
    counterpart_location_id: Optional[int] = None
    counterpart_location_name: Optional[str] = None
    qty: int
    balance_after: int
    location_balance_after: int
    purpose_type: Optional[str] = None
    unit_cost_snapshot: Decimal
    amount_snapshot: Decimal
    source_movement_id: Optional[int] = None
    source_type: Optional[str] = None
    source_id: Optional[int] = None
    transfer_key: Optional[str] = None
    memo: Optional[str] = None
    usage_product_display: str = "-"
    usage_lot_display: str = "-"
    usage_partner_display: str = "-"
    work_instruction_no: str = "-"
    work_group_seq: str = "-"
    created_by: str
    created_at: datetime


class SelfUseSheetMovementListOut(BaseModel):
    items: list[SelfUseSheetMovementOut]
    total: int
    page: int
    size: int


class SelfUseSheetTransferIn(BaseModel):
    expected_version: int = Field(..., ge=1)
    from_location_id: int = Field(..., ge=1)
    to_location_id: int = Field(..., ge=1)
    qty: int = Field(..., gt=0)
    reason: str = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_locations(self):
        if self.from_location_id == self.to_location_id:
            raise ValueError("from_location_id and to_location_id must be different")
        self.reason = self.reason.strip()
        return self
