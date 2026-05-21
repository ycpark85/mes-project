from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class AuthLoginRequest(BaseModel):
    login_id: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=200)


class AuthUserOut(BaseModel):
    user_id: int
    login_id: str
    user_name: str
    department: str | None = None
    position: str | None = None
    is_active: bool
    last_login_at: datetime | None = None

    class Config:
        from_attributes = True


class AuthRoleOut(BaseModel):
    role_id: int
    role_code: str
    role_name: str

    class Config:
        from_attributes = True


class AuthContextOut(BaseModel):
    user: AuthUserOut
    roles: list[AuthRoleOut]
    permissions: list[str]


class AuthLoginResponse(AuthContextOut):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int


class AuthMeResponse(AuthContextOut):
    pass