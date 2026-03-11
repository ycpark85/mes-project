from app.crud.base import BaseCRUD
from app.models.product import Product

product_crud = BaseCRUD(
    model=Product,
    pk_field="product_id",
    q_fields=["product_code", "product_name"],
    unique_conflict_message="product_code already exists",
)