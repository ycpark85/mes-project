from datetime import datetime
from pydantic import BaseModel, Field


class DrawingRevisionFileOut(BaseModel):
    revision_file_id: int
    revision_id: int
    file_kind: str
    file_uri: str
    original_filename: str
    content_type: str | None
    file_size: int | None
    created_at: datetime

    class Config:
        from_attributes = True


class DrawingRevisionFileListOut(BaseModel):
    items: list[DrawingRevisionFileOut]