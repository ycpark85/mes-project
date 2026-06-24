from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field


class OutsourceProcessingCostTargetOut(BaseModel):
    target_key: str
    process_type: str
    outsource_work_group_id: Optional[int] = None
    lot_id: Optional[int] = None
    instruction_no: Optional[str] = None
    instruction_date: Optional[date] = None
    partner_name: Optional[str] = None
    group_seq: Optional[str] = None
    is_bundle: bool = False
    lot_count: int = 0
    representative_lot_id: Optional[int] = None
    representative_lot_no: Optional[str] = None
    representative_product_name: Optional[str] = None
    lot_nos: List[str] = Field(default_factory=list)
    product_names: List[str] = Field(default_factory=list)
    product_specs: List[str] = Field(default_factory=list)
    sheet_qty: Optional[int] = None
    instruction_output_qty: Optional[int] = None
    allocation_basis_type: str
    allocation_basis_value: Decimal
    outsource_processing_cost_group_id: Optional[int] = None
    already_cost_group_no: Optional[str] = None
    cost_status: Optional[str] = None
    standard_amount: Optional[Decimal] = None
    actual_amount: Optional[Decimal] = None
    amount_difference: Optional[Decimal] = None
    settlement_month: Optional[date] = None
    allocations: List["OutsourceProcessingCostAllocationOut"] = Field(default_factory=list)


class OutsourceProcessingCostTargetListOut(BaseModel):
    items: List[OutsourceProcessingCostTargetOut] = Field(default_factory=list)


class OutsourceProcessingCostAllocationOut(BaseModel):
    outsource_processing_cost_allocation_id: Optional[int] = None
    lot_id: int
    lot_no: str
    product_code: Optional[str] = None
    product_name: Optional[str] = None
    product_spec: Optional[str] = None
    panel_width_mm: Optional[int] = None
    panel_length_mm: Optional[int] = None
    cuts_per_sheet: Optional[int] = None
    sheet_qty: Optional[int] = None
    instruction_output_qty: Optional[int] = None
    basis_type: str
    basis_value: Decimal
    basis_area_sqm: Optional[Decimal] = None
    allocation_ratio: Decimal
    standard_allocated_amount: Optional[Decimal] = None
    actual_allocated_amount: Optional[Decimal] = None
    amount_difference: Optional[Decimal] = None


OutsourceProcessingCostTargetOut.model_rebuild()


class OutsourceProcessingCostGroupListItemOut(BaseModel):
    outsource_processing_cost_group_id: int
    cost_group_no: str
    settlement_month: date
    process_type: str
    status: str
    work_group_count: int = 0
    lot_count: int = 0
    partner_names: List[str] = Field(default_factory=list)
    instruction_nos: List[str] = Field(default_factory=list)
    lot_nos: List[str] = Field(default_factory=list)
    product_names: List[str] = Field(default_factory=list)
    standard_amount: Optional[Decimal] = None
    actual_amount: Optional[Decimal] = None
    amount_difference: Optional[Decimal] = None
    standard_memo: Optional[str] = None
    actual_billing_month: Optional[date] = None
    actual_memo: Optional[str] = None
    remark: Optional[str] = None
    closed_at: Optional[datetime] = None
    canceled_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    allocations: List[OutsourceProcessingCostAllocationOut] = Field(default_factory=list)


class OutsourceProcessingCostGroupListOut(BaseModel):
    items: List[OutsourceProcessingCostGroupListItemOut] = Field(default_factory=list)
    total_count: int = 0
    standard_total: Decimal = Decimal("0")
    actual_total: Decimal = Decimal("0")
    difference_total: Decimal = Decimal("0")
    unclosed_count: int = 0


class OutsourceProcessingCostCreate(BaseModel):
    settlement_month: date
    process_type: str
    target_work_group_ids: List[int] = Field(default_factory=list)
    target_lot_ids: List[int] = Field(default_factory=list)
    standard_amount: Optional[Decimal] = Field(default=None, ge=0)
    standard_memo: Optional[str] = None
    actual_amount: Optional[Decimal] = Field(default=None, ge=0)
    actual_billing_month: Optional[date] = None
    actual_memo: Optional[str] = None
    remark: Optional[str] = None


class OutsourceProcessingCostUpdate(BaseModel):
    standard_amount: Optional[Decimal] = Field(default=None, ge=0)
    standard_memo: Optional[str] = None
    actual_amount: Optional[Decimal] = Field(default=None, ge=0)
    actual_billing_month: Optional[date] = None
    actual_memo: Optional[str] = None
    remark: Optional[str] = None
