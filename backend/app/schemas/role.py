from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.permission import PermissionOut


class RoleCreate(BaseModel):
    role_code: str = Field(..., min_length=1, max_length=50)
    role_name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    is_active: bool = True


class RoleUpdate(BaseModel):
    role_name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None
    is_active: bool | None = None


class RoleOut(BaseModel):
    role_id: int
    role_code: str
    role_name: str
    description: str | None = None
    is_system: bool
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class RoleListOut(BaseModel):
    items: list[RoleOut]
    total: int
    page: int
    size: int


class RolePermissionOut(BaseModel):
    role_id: int
    permissions: list[PermissionOut]


class RolePermissionUpdate(BaseModel):
    permission_ids: list[int] = Field(default_factory=list)