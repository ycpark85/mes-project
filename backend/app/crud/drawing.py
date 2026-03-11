from app.crud.base import BaseCRUD
from app.models.drawing import Drawing

drawing_crud = BaseCRUD(
    model=Drawing,
    pk_field="drawing_id",
    q_fields=["drawing_no"],
    unique_conflict_message="drawing_no already exists",
)