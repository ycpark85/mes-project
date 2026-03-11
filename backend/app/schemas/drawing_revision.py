from datetime import datetime
from pydantic import BaseModel


class DrawingRevisionOut(BaseModel):
    revision_id: int
    drawing_id: int
    rev_no: str
    file_uri: str
    created_at: datetime

    class Config:
        from_attributes = True


class DrawingRevisionListOut(BaseModel):
    items: list[DrawingRevisionOut]
    total: int
    page: int
    size: int