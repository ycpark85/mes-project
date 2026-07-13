from enum import Enum
from pydantic import BaseModel, ConfigDict, Field


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

    model_config = ConfigDict(from_attributes=True)


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


class PartnerBulkItem(BaseModel):
    row_number: int = Field(..., ge=1)
    partner_type: PartnerType
    name: str = Field(..., max_length=200)
    business_no: str = Field(..., max_length=20)
    is_active: bool = True


class PartnerBulkCreateRequest(BaseModel):
    items: list[PartnerBulkItem] = Field(..., min_length=1)


class PartnerBulkError(BaseModel):
    row_number: int
    field: str
    message: str


class PartnerBulkCreateResult(BaseModel):
    total_count: int
    success_count: int
    failure_count: int
    created_items: list[PartnerOut]
    errors: list[PartnerBulkError]
