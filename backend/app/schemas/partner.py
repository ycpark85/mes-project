from enum import Enum
from pydantic import BaseModel, Field


class PartnerType(str, Enum):
    CUSTOMER = "CUSTOMER"
    VENDOR = "VENDOR"


class PartnerCreate(BaseModel):
    partner_type: PartnerType
    name: str = Field(..., max_length=200)
    business_no: str | None = Field(None, max_length=20)
    is_active: bool = True


class PartnerOut(BaseModel):
    partner_id: int
    partner_type: PartnerType
    name: str
    business_no: str | None
    is_active: bool

    class Config:
        from_attributes = True

class PartnerListOut(BaseModel):
    items: list[PartnerOut]
    total: int
    page: int
    size: int

class PartnerUpdate(BaseModel):
    partner_type: PartnerType | None = None
    name: str | None = Field(None, max_length=200)
    business_no: str | None = Field(None, max_length=20)
    is_active: bool | None = None