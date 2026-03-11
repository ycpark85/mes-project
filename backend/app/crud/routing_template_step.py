from app.crud.base import BaseCRUD
from app.models.routing_template_step import RoutingTemplateStep

routing_template_step_crud = BaseCRUD(
    model=RoutingTemplateStep,
    pk_field="routing_template_step_id",
    q_fields=["default_process_type"],  # q 검색은 크게 의미 없지만 BaseCRUD 요구 형식상 둠
    unique_conflict_message="step_seq already exists in this template",
)