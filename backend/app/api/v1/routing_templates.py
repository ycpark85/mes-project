from fastapi import APIRouter, Depends, Query, Path, status, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func,select
from sqlalchemy.exc import IntegrityError

from app.db.session import get_db
from app.models.routing_template import RoutingTemplate
from app.models.routing_template_step import RoutingTemplateStep
from app.models.process import Process

from app.schemas.routing_template import (
    RoutingTemplateCreate,
    RoutingTemplateUpdate,
    RoutingTemplateOut,
    RoutingTemplateListOut,
)
from app.schemas.routing_template_step import (
    RoutingTemplateStepCreate,
    RoutingTemplateStepUpdate,
    RoutingTemplateStepOut,
    RoutingTemplateStepListOut,
)

from app.crud.routing_template import routing_template_crud
from app.crud.routing_template_step import routing_template_step_crud

router = APIRouter(prefix="/routing-templates", tags=["RoutingTemplate"])


def _ensure_process_exists(db: Session, process_id: int):
    if not db.query(Process.process_id).filter(Process.process_id == process_id, Process.is_active == True).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="process_id not found")


# --------------------
# Template CRUD
# --------------------
@router.post("", response_model=RoutingTemplateOut, status_code=status.HTTP_201_CREATED)
def create_template(payload: RoutingTemplateCreate, db: Session = Depends(get_db)):
    obj = RoutingTemplate(
        template_code=payload.template_code,
        template_name=payload.template_name,
        is_active=payload.is_active,
    )
    return routing_template_crud.create(db, obj)


@router.get("/{routing_template_id}", response_model=RoutingTemplateOut)
def get_template(
    routing_template_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    return routing_template_crud.get_or_404(db, routing_template_id, active_only=True)


@router.get("", response_model=RoutingTemplateListOut)
def list_templates(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    q: str | None = Query(None),
    is_active: bool | None = Query(True),
    db: Session = Depends(get_db),
):
    items, total = routing_template_crud.list_paged(db, page=page, size=size, q=q, is_active=is_active)
    return {"items": items, "total": total, "page": page, "size": size}


@router.patch("/{routing_template_id}", response_model=RoutingTemplateOut)
def update_template(
    routing_template_id: int = Path(..., ge=1),
    payload: RoutingTemplateUpdate = None,
    db: Session = Depends(get_db),
):
    obj = routing_template_crud.get_or_404(db, routing_template_id, active_only=False)

    if payload.template_name is not None:
        obj.template_name = payload.template_name
    if payload.is_active is not None:
        obj.is_active = payload.is_active

    return routing_template_crud.commit(db, obj)


@router.delete("/{routing_template_id}", response_model=RoutingTemplateOut)
def delete_template(
    routing_template_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    return routing_template_crud.soft_delete(db, routing_template_id)


# --------------------
# Step CRUD (nested)
# --------------------
@router.post("/{routing_template_id}/steps", response_model=RoutingTemplateStepOut, status_code=status.HTTP_201_CREATED)
def create_step(
    routing_template_id: int = Path(..., ge=1),
    payload: RoutingTemplateStepCreate = None,
    db: Session = Depends(get_db),
):
    # template 존재 검증(삭제 포함 여부는 운영 정책: 여기선 active_only=False로)
    routing_template_crud.get_or_404(db, routing_template_id, active_only=False)
    # ✅ process row 조회(존재 + 활성)
    proc = (
        db.query(Process)
        .filter(Process.process_id == payload.process_id, Process.is_active == True)
        .first()
    )
    if not proc:
        raise HTTPException(status_code=400, detail="process_id not found")

    # (호환) payload로 default_process_type이 들어오면 불일치 방지
    incoming_dpt = getattr(payload, "default_process_type", None)
    if incoming_dpt is not None:
        incoming = incoming_dpt.value if hasattr(incoming_dpt, "value") else str(incoming_dpt)
        if incoming != proc.process_type:
            raise HTTPException(
                status_code=409,
                detail="default_process_type must match process.process_type",
        )

    obj = RoutingTemplateStep(
        routing_template_id=routing_template_id,
        step_seq=payload.step_seq,
        process_id=payload.process_id,
        default_process_type=proc.process_type,  
        is_active=payload.is_active,
    )

    # step은 uq(step_seq) 충돌 가능성이 커서 409를 명확히
    try:
        db.add(obj)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="step_seq already exists in this template")

    db.refresh(obj)
    return obj


@router.get("/{routing_template_id}/steps", response_model=RoutingTemplateStepListOut)
def list_steps(
    routing_template_id: int = Path(..., ge=1),
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=200),
    is_active: bool | None = Query(True),
    db: Session = Depends(get_db),
):
    # template 존재만 확인
    routing_template_crud.get_or_404(db, routing_template_id, active_only=False)

    base = db.query(RoutingTemplateStep).filter(RoutingTemplateStep.routing_template_id == routing_template_id)

    if is_active is not None:
        base = base.filter(RoutingTemplateStep.is_active == is_active)

    total = base.with_entities(func.count()).scalar() or 0
    items = (
        base.order_by(RoutingTemplateStep.step_seq.asc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )
    return {"items": items, "total": total, "page": page, "size": size}


@router.patch("/{routing_template_id}/steps/{routing_template_step_id}", response_model=RoutingTemplateStepOut)
def update_step(
    routing_template_id: int,
    routing_template_step_id: int,
    payload: RoutingTemplateStepUpdate,
    db: Session = Depends(get_db),
):
    # 1) Step 로드 + 소속 라우팅템플릿 검증
    step = db.execute(
        select(RoutingTemplateStep).where(
            RoutingTemplateStep.routing_template_step_id == routing_template_step_id,
            RoutingTemplateStep.routing_template_id == routing_template_id,
        )
    ).scalar_one_or_none()

    if not step:
        raise HTTPException(status_code=404, detail="RoutingTemplateStep not found")

    # 2) payload에 default_process_type 필드가 "있을 수도/없을 수도" 있으므로 안전하게 가져옴
    incoming_dpt = getattr(payload, "default_process_type", None)

    # 3) Step seq 업데이트
    if payload.step_seq is not None:
        step.step_seq = payload.step_seq

    # 4) process_id 변경 처리
    # - SSOT: default_process_type은 process.process_type에서 서버가 결정
    # - 따라서 process_id가 바뀌면 step.default_process_type도 자동 갱신
    process = None
    if payload.process_id is not None:
        process = db.execute(
            select(Process).where(
                Process.process_id == payload.process_id,
                Process.is_active == True,  # noqa: E712
            )
        ).scalar_one_or_none()

        if not process:
            raise HTTPException(status_code=404, detail="Process not found")

        step.process_id = process.process_id
        step.default_process_type = process.process_type

    # 5) default_process_type이 들어온 경우는 "검증"만 수행
    #    - process_id를 같이 보냈으면 위에서 이미 process를 구했으니 그걸 사용
    #    - process_id 없이 default_process_type만 보냈으면 현재 step.process_id 기준으로 process를 조회해서 검증
    if incoming_dpt is not None:
        # process_id가 없는 상태에서 default_process_type만 수정하려는 경우를 방지/검증
        if payload.process_id is None:
            # 현재 step.process_id 기반 process 조회
            process = db.execute(
                select(Process).where(
                    Process.process_id == step.process_id,
                    Process.is_active == True,  # noqa: E712
                )
            ).scalar_one_or_none()

            if not process:
                raise HTTPException(status_code=404, detail="Process not found")

        incoming = incoming_dpt.value if hasattr(incoming_dpt, "value") else str(incoming_dpt)

        if incoming != process.process_type:
            raise HTTPException(
                status_code=409,
                detail="default_process_type must match process.process_type",
            )
        # NOTE: 일치하면 통과만. 값을 step에 set하지 않음(SSOT 유지)

    # 6) 활성/비활성
    if payload.is_active is not None:
        step.is_active = payload.is_active

    # 7) 저장
    try:
        db.add(step)
        db.commit()
        db.refresh(step)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Integrity conflict")

    return step


@router.delete("/{routing_template_id}/steps/{routing_template_step_id}", response_model=RoutingTemplateStepOut)
def delete_step(
    routing_template_id: int = Path(..., ge=1),
    routing_template_step_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    routing_template_crud.get_or_404(db, routing_template_id, active_only=False)

    obj = (
        db.query(RoutingTemplateStep)
        .filter(
            RoutingTemplateStep.routing_template_step_id == routing_template_step_id,
            RoutingTemplateStep.routing_template_id == routing_template_id,
        )
        .first()
    )
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="RoutingTemplateStep not found"
        )

    db.delete(obj)
    db.commit()
    return obj