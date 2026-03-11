from app.crud.base import BaseCRUD
from app.models.process import Process

process_crud = BaseCRUD(
    model=Process,
    pk_field="process_id",
    q_fields=["process_code", "process_name"],
    unique_conflict_message="process_code already exists",
)