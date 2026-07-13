from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ShipmentCoaOut(BaseModel):
    shipment_coa_id: int
    order_line_id: int
    product_id: int

    product_name_snapshot: str
    product_spec_snapshot: str
    material_snapshot: str
    partner_name_snapshot: str

    lot_nos_snapshot: str
    stock_lot_nos_snapshot: Optional[str] = None
    production_lot_nos_snapshot: Optional[str] = None

    quantity_snapshot: int
    inspection_date_snapshot: date
    is_printed_product_snapshot: bool = False

    issued_at: datetime
    updated_at: datetime
    memo: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ShipmentCoaUpdateRequest(BaseModel):
    quantity_snapshot: int = Field(..., ge=0)
    inspection_date_snapshot: date
    memo: Optional[str] = None
