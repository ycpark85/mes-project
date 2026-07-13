from pydantic import BaseModel, ConfigDict, Field


class DefectTypeCreate(BaseModel):
    code: str = Field(..., max_length=50)
    category1_name: str = Field(..., max_length=200)
    category2_name: str = Field(..., max_length=200)
    memo: str | None = None
    is_active: bool = True


class DefectTypeUpdate(BaseModel):
    category1_name: str | None = Field(None, max_length=200)
    category2_name: str | None = Field(None, max_length=200)
    memo: str | None = None
    is_active: bool | None = None


class DefectTypeOut(BaseModel):
    defect_type_id: int
    code: str
    category1_name: str
    category2_name: str
    memo: str | None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class DefectTypeListOut(BaseModel):
    items: list[DefectTypeOut]
    total: int
    page: int
    size: int
