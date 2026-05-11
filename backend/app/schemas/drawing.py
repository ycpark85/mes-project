from datetime import datetime
from pydantic import BaseModel, Field


class DrawingCreate(BaseModel):
    drawing_no: str = Field(..., max_length=60)
    is_active: bool = True


class DrawingUpdate(BaseModel):
    drawing_no: str | None = Field(None, max_length=60)
    is_active: bool | None = None


class DrawingOut(BaseModel):
    drawing_id: int
    drawing_no: str
    current_revision_id: int | None
    current_revision_no: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DrawingListOut(BaseModel):
    items: list[DrawingOut]
    total: int
    page: int
    size: int