from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserRoleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    role_id: int
    role_code: str
    role_name: str


class UserRoleOptionOut(BaseModel):
    role_id: int
    role_code: str
    role_name: str


class UserVendorAccessOut(BaseModel):
    partner_id: int
    partner_name: str
    is_active: bool


class UserCreate(BaseModel):
    login_id: str = Field(..., min_length=1, max_length=50)
    user_name: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=6, max_length=200)

    role_ids: list[int] = Field(default_factory=list)

    department: str | None = Field(None, max_length=100)
    position: str | None = Field(None, max_length=100)
    is_active: bool = True
    is_vendor_user: bool = False
    vendor_partner_id: int | None = Field(None, ge=1)
    vendor_access_active: bool = True


class UserUpdate(BaseModel):
    user_name: str | None = Field(None, min_length=1, max_length=100)

    role_ids: list[int] | None = None

    department: str | None = Field(None, max_length=100)
    position: str | None = Field(None, max_length=100)
    is_active: bool | None = None
    is_vendor_user: bool | None = None
    vendor_partner_id: int | None = Field(None, ge=1)
    vendor_access_active: bool | None = None


class UserResetPassword(BaseModel):
    new_password: str = Field(..., min_length=6, max_length=200)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    login_id: str
    user_name: str

    department: str | None = None
    position: str | None = None

    is_active: bool
    password_change_required: bool = False
    last_login_at: datetime | None = None

    created_at: datetime | None = None
    updated_at: datetime | None = None

    roles: list[UserRoleOut] = Field(default_factory=list)
    vendor_access: UserVendorAccessOut | None = None

class UserListOut(BaseModel):
    items: list[UserOut]
    total: int
    page: int
    size: int
