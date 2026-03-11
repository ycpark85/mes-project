from app.crud.base import BaseCRUD
from app.models.defect_type import DefectType

defect_type_crud = BaseCRUD(
    model=DefectType,
    pk_field="defect_type_id",
    q_fields=["code", "name"],
    unique_conflict_message="defect_type code already exists",
)