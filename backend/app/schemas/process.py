from enum import Enum
from pydantic import BaseModel, Field


class ProcessType(str, Enum):
    INTERNAL = "INTERNAL"
    OUTSOURCE = "OUTSOURCE"


class ProcessCreate(BaseModel):
    process_code: str = Field(..., max_length=50)
    process_name: str = Field(..., max_length=200)
    process_type: ProcessType
    is_active: bool = True


class ProcessUpdate(BaseModel):
    process_name: str | None = Field(None, max_length=200)
    process_type: ProcessType | None = None
    is_active: bool | None = None


class ProcessOut(BaseModel):
    process_id: int
    process_code: str
    process_name: str
    process_type: ProcessType
    is_active: bool

    class Config:
        from_attributes = True


class ProcessListOut(BaseModel):
    items: list[ProcessOut]
    total: int
    page: int
    size: int