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

from app.core.auth import require_any_permission, require_permission

router = APIRouter()

# 인증 예외
router.include_router(health_router)
router.include_router(auth_router)

# 회원 / 역할 / 권한 관리는 각 endpoint 내부에서 세부 권한 검증
router.include_router(user_router)
router.include_router(permission_router)
router.include_router(role_router)

# 주요 업무 API VIEW 권한 적용
router.include_router(
    dashboard_router,
    dependencies=[Depends(require_permission("DASHBOARD.VIEW"))],
)

router.include_router(
    defect_type_router,
    dependencies=[Depends(require_permission("DEFECT_TYPES.VIEW"))],
)

router.include_router(
    process_router,
    dependencies=[Depends(require_permission("PROCESSES.VIEW"))],
)

router.include_router(
    partner_router,
    dependencies=[Depends(require_permission("PARTNERS.VIEW"))],
)

router.include_router(
    routing_template_router,
    dependencies=[
        Depends(
            require_any_permission(
                "ROUTING_TEMPLATES.VIEW",
                "ROUTING_TEMPLATE_STEPS.VIEW",
            )
        )
    ],
)

router.include_router(
    drawing_router,
    dependencies=[Depends(require_permission("DRAWINGS.VIEW"))],
)

router.include_router(
    drawing_revision_router,
    dependencies=[Depends(require_permission("DRAWINGS.VIEW"))],
)

router.include_router(
    product_router,
    dependencies=[
        Depends(
            require_any_permission(
                "PRODUCTS.VIEW",
                "PRODUCT_MONITORING.VIEW",
            )
        )
    ],
)

router.include_router(
    order_line_router,
    dependencies=[
        Depends(
            require_any_permission(
                "ORDER_LINE_CREATE.VIEW",
                "ORDER_LINE_LIST.VIEW",
            )
        )
    ],
)

router.include_router(
    lot_router,
    dependencies=[Depends(require_permission("LOTS.VIEW"))],
)

router.include_router(
    lot_step_router,
    dependencies=[Depends(require_permission("LOTS.VIEW"))],
)

router.include_router(
    inspection_schedule_router,
    dependencies=[
        Depends(
            require_any_permission(
                "INSPECTION_WORK_INSTRUCTIONS.VIEW",
                "INSPECTION_SCHEDULES.VIEW",
            )
        )
    ],
)

router.include_router(
    inspection_result_router,
    dependencies=[
        Depends(
            require_any_permission(
                "INSPECTION_WORK_INSTRUCTIONS.VIEW",
                "INSPECTION_SCHEDULES.VIEW",
            )
        )
    ],
)

router.include_router(
    outsource_work_instruction_router,
    dependencies=[
        Depends(
            require_any_permission(
                "OUTSOURCE_WORK_INSTRUCTIONS.VIEW",
                "OUTSOURCE_PURCHASE_ORDERS.VIEW",
                "OUTSOURCE_PURCHASE_ORDER_LIST.VIEW",
                "BOHYUN_OUTSOURCE_MANAGEMENT.VIEW",
                "BOHYUN_OUTSOURCE_SHIPMENT_LIST.VIEW",
            )
        )
    ],
)

router.include_router(
    inventory_router,
    dependencies=[Depends(require_permission("INVENTORIES.VIEW"))],
)

router.include_router(
    shipment_router,
    dependencies=[Depends(require_permission("SHIPMENTS.VIEW"))],
)