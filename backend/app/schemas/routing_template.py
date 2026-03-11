from pydantic import BaseModel, Field


class RoutingTemplateCreate(BaseModel):
    template_code: str = Field(..., max_length=50)
    template_name: str = Field(..., max_length=100)
    is_active: bool = True


class RoutingTemplateUpdate(BaseModel):
    template_name: str | None = Field(None, max_length=100)
    is_active: bool | None = None


class RoutingTemplateOut(BaseModel):
    routing_template_id: int
    template_code: str
    template_name: str
    is_active: bool

    class Config:
        from_attributes = True


class RoutingTemplateListOut(BaseModel):
    items: list[RoutingTemplateOut]
    total: int
    page: int
    size: int