from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ProductInventoryOut(BaseModel):
    product_id: int
    product_code: str
    product_name: str
    uom: str
    current_qty: int = 0
    updated_at: Optional[datetime] = None


class ProductInventoryListOut(BaseModel):
    items: list[ProductInventoryOut]
    total: int
    page: int
    size: int


class ProductInventoryMovementOut(BaseModel):
    inventory_movement_id: int
    product_id: int
    product_inventory_lot_id: Optional[int] = None
    stock_lot_no: Optional[str] = None
    product_code: Optional[str] = None
    product_name: Optional[str] = None
    movement_type: str
    qty: int
    balance_after: int
    source_type: Optional[str] = None
    source_id: Optional[int] = None
    order_line_id: Optional[int] = None
    inspection_schedule_id: Optional[int] = None
    inspection_result_id: Optional[int] = None
    memo: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductInventoryMovementListOut(BaseModel):
    items: list[ProductInventoryMovementOut]
    total: int
    page: int
    size: int


class ProductInventoryAdjustmentIn(BaseModel):
    qty: int = Field(..., gt=0)
    stock_lot_no: Optional[str] = Field(default=None, max_length=100)
    memo: Optional[str] = None


class ProductInventoryConsistencyOut(BaseModel):
    product_id: int
    product_code: str
    product_name: str
    current_qty: int
    lot_qty: int
    movement_qty: int
    diff_qty: int


class ProductInventoryConsistencyListOut(BaseModel):
    items: list[ProductInventoryConsistencyOut]
    total: int

class InitialInventoryBulkItemIn(BaseModel):
    row_number: int
    product_code: str
    lot_no: str = Field(..., max_length=100)
    initial_qty: int = Field(..., ge=0)
    memo: Optional[str] = None


class InitialInventoryBulkIn(BaseModel):
    items: list[InitialInventoryBulkItemIn]


class InitialInventoryBulkErrorOut(BaseModel):
    row_number: int
    product_code: Optional[str] = None
    lot_no: Optional[str] = None
    message: str


class InitialInventoryBulkResultOut(BaseModel):
    total_count: int
    success_count: int
    skipped_count: int
    failure_count: int
    errors: list[InitialInventoryBulkErrorOut] = []
