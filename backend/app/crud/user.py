from app.crud.base import BaseCRUD
from app.models.user import User


user_crud = BaseCRUD(
    model=User,
    pk_field="user_id",
    q_fields=["login_id", "user_name", "department", "position"],
    unique_conflict_message="login_id already exists",
)