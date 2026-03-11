from app.crud.base import BaseCRUD
from app.models.partner import Partner

partner_crud = BaseCRUD(
    model=Partner,
    pk_field="partner_id",
    q_fields=["name", "business_no"],
    unique_conflict_message="business_no already exists",
)