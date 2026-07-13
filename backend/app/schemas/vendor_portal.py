from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field
from decimal import Decimal


class VendorPortalBohyunWorkDone(BaseModel):
    work_done_sheet_qty: int = Field(..., ge=0)
    outsource_processing_fee: Optional[Decimal] = Field(default=None, ge=0)
    remark: Optional[str] = None
