from pydantic import BaseModel, Field
from typing import Optional


class ProductCreate(BaseModel):
    product_code: str = Field(..., max_length=60)
    product_name: str = Field(..., max_length=200)
    uom: str = Field(..., max_length=10)

    drawing_id: int = Field(..., ge=1)
    routing_template_id: int = Field(..., ge=1)

    panel_width_mm: Optional[int] = Field(None, ge=0)
    panel_length_mm: Optional[int] = Field(None, ge=0)
    product_spec: Optional[str] = Field(None, max_length=100)
    cut_qty_per_panel: Optional[int] = Field(None, ge=0)

    is_active: bool = True
    memo: Optional[str] = None


class ProductUpdate(BaseModel):
    product_name: Optional[str] = Field(None, max_length=200)
    uom: Optional[str] = Field(None, max_length=10)

    drawing_id: Optional[int] = Field(None, ge=1)
    routing_template_id: Optional[int] = Field(None, ge=1)

    panel_width_mm: Optional[int] = Field(None, ge=0)
    panel_length_mm: Optional[int] = Field(None, ge=0)
    product_spec: Optional[str] = Field(None, max_length=100)
    cut_qty_per_panel: Optional[int] = Field(None, ge=0)

    is_active: Optional[bool] = None
    memo: Optional[str] = None


class ProductOut(BaseModel):
    product_id: int
    product_code: str
    product_name: str
    uom: str

    drawing_id: int
    routing_template_id: int

    panel_width_mm: Optional[int] = None
    panel_length_mm: Optional[int] = None
    product_spec: Optional[str] = None
    cut_qty_per_panel: Optional[int] = None

    is_active: bool
    memo: Optional[str] = None

    class Config:
        from_attributes = True


class ProductListOut(BaseModel):
    items: list[ProductOut]
    total: int
    page: int
    size: int