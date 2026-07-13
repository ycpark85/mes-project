from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PermissionOut(BaseModel):
    permission_id: int
    permission_code: str
    menu_code: str
    action_code: str
    permission_name: str
    sort_order: int
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class PermissionListOut(BaseModel):
    items: list[PermissionOut]
    total: int
    page: int
    size: int
