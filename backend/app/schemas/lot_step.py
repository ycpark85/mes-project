from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class LotStepOut(BaseModel):
    lot_step_id: int
    lot_id: int
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