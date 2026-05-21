from fastapi import APIRouter, Depends

from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as user_router
from app.api.v1.permissions import router as permission_router
from app.api.v1.roles import router as role_router
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

from app.core.auth import get_current_user


router = APIRouter()

router.include_router(health_router)
router.include_router(auth_router)

router.include_router(user_router)
router.include_router(permission_router)
router.include_router(role_router)


router.include_router(partner_router,
    dependencies=[Depends(get_current_user)],)
router.include_router(process_router,
    dependencies=[Depends(get_current_user)],)
router.include_router(routing_template_router,
    dependencies=[Depends(get_current_user)],)
router.include_router(drawing_router,
    dependencies=[Depends(get_current_user)],)
router.include_router(drawing_revision_router,
    dependencies=[Depends(get_current_user)],)
router.include_router(product_router,
    dependencies=[Depends(get_current_user)],)
router.include_router(order_line_router,
    dependencies=[Depends(get_current_user)],)
router.include_router(lot_router,
    dependencies=[Depends(get_current_user)],)
router.include_router(lot_step_router,
    dependencies=[Depends(get_current_user)],)
router.include_router(inspection_schedule_router,
    dependencies=[Depends(get_current_user)],)
router.include_router(inspection_result_router,
    dependencies=[Depends(get_current_user)],)
router.include_router(defect_type_router,
    dependencies=[Depends(get_current_user)],)
router.include_router(outsource_work_instruction_router,
    dependencies=[Depends(get_current_user)],)
router.include_router(dashboard_router,
    dependencies=[Depends(get_current_user)],)
router.includeRouter(inventory_router,
    dependencies=[Depends(get_current_user)],)
router.includeRouter(shipment_router,
    dependencies=[Depends(get_current_user)],)