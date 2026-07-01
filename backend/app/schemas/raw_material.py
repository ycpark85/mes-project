from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class RawMaterialCreate(BaseModel):
    material_code: str = Field(..., min_length=1, max_length=60)
    material_name: str = Field(..., min_length=1, max_length=200)
    material_spec: Optional[str] = Field(default=None, max_length=100)
    width_mm: Optional[int] = Field(default=None, ge=0)
    material_type: Optional[str] = Field(default=None, max_length=100)
    uom: str = Field(default="M", min_length=1, max_length=10)
    standard_unit_cost: Optional[Decimal] = Field(default=None, ge=0)
    is_active: bool = True
    memo: Optional[str] = None


class RawMaterialUpdate(BaseModel):
    material_name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    material_spec: Optional[str] = Field(default=None, max_length=100)
    width_mm: Optional[int] = Field(default=None, ge=0)
    material_type: Optional[str] = Field(default=None, max_length=100)
    uom: Optional[str] = Field(default=None, min_length=1, max_length=10)
    standard_unit_cost: Optional[Decimal] = Field(default=None, ge=0)
    is_active: Optional[bool] = None
    memo: Optional[str] = None


class RawMaterialOut(BaseModel):
    raw_material_id: int
    material_code: str
    material_name: str
    material_spec: Optional[str] = None
    width_mm: Optional[int] = None
    material_type: Optional[str] = None
    uom: str
    standard_unit_cost: Optional[Decimal] = None
    is_active: bool
    memo: Optional[str] = None
    current_qty: Decimal = Decimal("0")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RawMaterialListOut(BaseModel):
    items: list[RawMaterialOut]
    total: int
    page: int
    size: int


class RawMaterialLocationCreate(BaseModel):
    location_code: Optional[str] = Field(default=None, max_length=60)
    location_name: str = Field(..., min_length=1, max_length=200)
    location_type: str = Field(..., min_length=1, max_length=30)
    partner_id: Optional[int] = None
    is_active: bool = True
    memo: Optional[str] = None


class RawMaterialLocationUpdate(BaseModel):
    location_name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    location_type: Optional[str] = Field(default=None, min_length=1, max_length=30)
    partner_id: Optional[int] = None
    is_active: Optional[bool] = None
    memo: Optional[str] = None


class RawMaterialLocationOut(BaseModel):
    raw_material_location_id: int
    location_code: str
    location_name: str
    location_type: str
    partner_id: Optional[int] = None
    partner_name: Optional[str] = None
    is_active: bool
    memo: Optional[str] = None
    current_qty: Decimal = Decimal("0")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RawMaterialLocationListOut(BaseModel):
    items: list[RawMaterialLocationOut]
    total: int
    page: int
    size: int


class RawMaterialInventoryLotOut(BaseModel):
    raw_material_inventory_lot_id: int
    raw_material_id: int
    raw_material_location_id: int
    material_code: str
    material_name: str
    material_spec: Optional[str] = None
    width_mm: Optional[int] = None
    uom: str
    location_code: str
    location_name: str
    location_type: str
    lot_no: str
    current_qty: Decimal
    unit_cost: Optional[Decimal] = None
    inventory_amount: Optional[Decimal] = None
    received_at: Optional[date] = None
    updated_at: datetime


class RawMaterialInventoryLotListOut(BaseModel):
    items: list[RawMaterialInventoryLotOut]
    total: int
    page: int
    size: int


class RawMaterialMovementOut(BaseModel):
    raw_material_inventory_movement_id: int
    raw_material_id: int
    raw_material_location_id: int
    raw_material_inventory_lot_id: Optional[int] = None
    material_code: Optional[str] = None
    material_name: Optional[str] = None
    location_name: Optional[str] = None
    lot_no: Optional[str] = None
    movement_type: str
    qty: Decimal
    balance_after: Decimal
    unit_cost_snapshot: Optional[Decimal] = None
    amount_snapshot: Optional[Decimal] = None
    source_type: Optional[str] = None
    source_id: Optional[int] = None
    transfer_key: Optional[str] = None
    memo: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class RawMaterialMovementListOut(BaseModel):
    items: list[RawMaterialMovementOut]
    total: int
    page: int
    size: int


class RawMaterialInboundIn(BaseModel):
    raw_material_id: int
    raw_material_location_id: int
    lot_no: str = Field(..., min_length=1, max_length=100)
    qty: Decimal = Field(..., gt=0)
    unit_cost: Optional[Decimal] = Field(default=None, ge=0)
    received_at: Optional[date] = None
    memo: Optional[str] = None


class RawMaterialTransferIn(BaseModel):
    raw_material_inventory_lot_id: int
    to_location_id: int
    qty: Decimal = Field(..., gt=0)
    memo: Optional[str] = None


class RawMaterialAdjustmentIn(BaseModel):
    raw_material_inventory_lot_id: int
    qty: Decimal = Field(..., gt=0)
    memo: Optional[str] = None
