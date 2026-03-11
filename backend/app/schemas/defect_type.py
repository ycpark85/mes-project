from pydantic import BaseModel, Field


class DefectTypeCreate(BaseModel):
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=200)
    memo: str | None = None
    is_active: bool = True


class DefectTypeUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    memo: str | None = None
    is_active: bool | None = None


class DefectTypeOut(BaseModel):
    defect_type_id: int
    code: str
    name: str
    memo: str | None
    is_active: bool

    class Config:
        from_attributes = True


class DefectTypeListOut(BaseModel):
    items: list[DefectTypeOut]
    total: int
    page: int
    size: int