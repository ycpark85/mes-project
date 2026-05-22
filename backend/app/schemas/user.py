from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class UserRoleOut(BaseModel):
    role_id: int
    role_code: str
    role_name: str

    class Config:
        from_attributes = True


class UserRoleOptionOut(BaseModel):
    role_id: int
    role_code: str
    role_name: str


class UserCreate(BaseModel):
    login_id: str = Field(..., min_length=1, max_length=50)
    user_name: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=6, max_length=200)

    role_ids: list[int] = Field(default_factory=list)

    department: str | None = Field(None, max_length=100)
    position: str | None = Field(None, max_length=100)
    is_active: bool = True


class UserUpdate(BaseModel):
    user_name: str | None = Field(None, min_length=1, max_length=100)

    role_ids: list[int] | None = None

    department: str | None = Field(None, max_length=100)
    position: str | None = Field(None, max_length=100)
    is_active: bool | None = None


class UserResetPassword(BaseModel):
    new_password: str = Field(..., min_length=6, max_length=200)


class UserOut(BaseModel):
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

    class Config:
        from_attributes = True


class UserListOut(BaseModel):
    items: list[UserOut]
    total: int
    page: int
    size: int