from fastapi import APIRouter
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.partners_lagacy import router as partner_router
from app.api.v1.processes import router as process_router
from app.api.v1.routing_templates import router as routing_template_router
from app.api.v1.drawings import router as drawing_router
from app.api.v1.drawing_revisions import router as drawing_revision_router
from app.api.v1.products import router as product_router
from app.api.v1.order_lines import router as order_line_router
from app.api.v1.lots import router as lot_router
from app.api.v1.lot_steps import router as lot_step_router
from app.api.v1.inspection_schedules import router as inspection_schedule_router
from app.api.v1.inspection_results import router as inspection_result_router
from app.api.v1.defect_types import router as defect_type_router
from app.api.v1.outsource_work_instructions import router as outsource_work_instruction_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.inventories import router as inventory_router
from app.api.v1.shipments import router as shipment_router

router = APIRouter()
router.include_router(health_router)
router.include_router(partner_router)
router.include_router(process_router)
router.include_router(routing_template_router)
router.include_router(drawing_router)
router.include_router(drawing_revision_router)
router.include_router(product_router)
router.include_router(order_line_router)
router.include_router(lot_router)
router.include_router(lot_step_router)
router.include_router(inspection_schedule_router)
router.include_router(inspection_result_router)
router.include_router(defect_type_router)
router.include_router(outsource_work_instruction_router)
router.include_router(dashboard_router)
router.include_router(inventory_router)
router.include_router(shipment_router)