from pydantic import BaseModel, Field
from enum import Enum


class DefaultProcessType(str, Enum):
    OUTSOURCE = "OUTSOURCE"
    INTERNAL = "INTERNAL"


class RoutingTemplateStepCreate(BaseModel):
    step_seq: int = Field(..., gt=0)  # DB 체크와 동일
    process_id: int
    is_active: bool = True


class RoutingTemplateStepUpdate(BaseModel):
    step_seq: int | None = Field(None, gt=0)
    process_id: int | None = None
    is_active: bool | None = None


class RoutingTemplateStepOut(BaseModel):
    routing_template_step_id: int
    routing_template_id: int
    step_seq: int
    process_id: int
    default_process_type: DefaultProcessType
    is_active: bool

    class Config:
        from_attributes = True


class RoutingTemplateStepListOut(BaseModel):
    items: list[RoutingTemplateStepOut]
    total: int
    page: int
    size: int