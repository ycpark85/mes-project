from datetime import datetime
from pydantic import BaseModel, Field

from app.schemas.drawing_revision_file import DrawingRevisionFileOut


class DrawingRevisionCreate(BaseModel):
    rev_no: str = Field(..., max_length=20)
    set_as_current: bool = True


class DrawingRevisionOut(BaseModel):
    revision_id: int
    drawing_id: int
    rev_no: str
    file_uri: str
    created_at: datetime
    files: list[DrawingRevisionFileOut] = []

    class Config:
        from_attributes = True


class DrawingRevisionListOut(BaseModel):
    items: list[DrawingRevisionOut]
    total: int
    page: int
    size: int