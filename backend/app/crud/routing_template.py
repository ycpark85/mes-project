from app.crud.base import BaseCRUD
from app.models.routing_template import RoutingTemplate

routing_template_crud = BaseCRUD(
    model=RoutingTemplate,
    pk_field="routing_template_id",
    q_fields=["template_code", "template_name"],
    unique_conflict_message="template_code already exists",
)