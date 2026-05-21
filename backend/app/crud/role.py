from app.crud.base import BaseCRUD
from app.models.role import Role


role_crud = BaseCRUD(
    model=Role,
    pk_field="role_id",
    q_fields=["role_code", "role_name", "description"],
    unique_conflict_message="role_code already exists",
)