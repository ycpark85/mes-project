from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.orm import Session, aliased, selectinload
from sqlalchemy import BigInteger, and_, case, cast, desc, func, nullslast, or_
from app.db.session import get_db
from app.models.drawing import Drawing
from app.models.drawing_revision import DrawingRevision
from app.models.drawing_rivision_file import DrawingRevisionFile
from app.models.product import Product
from app.schemas.drawing import (
    DrawingCreate,
    DrawingUpdate,
    DrawingOut,
    DrawingListOut,
    PendingNewDrawingListOut,
)
from app.crud.drawing import drawing_crud

router = APIRouter(prefix="/drawings", tags=["Drawing"])

def _drawing_no_order():
    numeric_suffix = case(
        (
            Drawing.drawing_no.op("~")(r"[0-9]+$"),
            cast(
                func.regexp_replace(
                    Drawing.drawing_no,
                    r"^.*?([0-9]+)$",
                    r"\1",
                ),
                BigInteger,
            ),
        ),
        else_=None,
    )

    return (
        nullslast(desc(numeric_suffix)),
        Drawing.drawing_no.desc(),
        Drawing.drawing_id.desc(),
    )


@router.post("", response_model=DrawingOut, status_code=status.HTTP_201_CREATED)
def create_drawing(payload: DrawingCreate, db: Session = Depends(get_db)):
    obj = Drawing(
        drawing_no=payload.drawing_no,
        is_active=payload.is_active,
    )
    return drawing_crud.create(db, obj)


@router.get("/pending-new", response_model=PendingNewDrawingListOut)
def list_pending_new_drawings(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    q: str | None = Query(None),
    db: Session = Depends(get_db),
):
    drawing_file = aliased(DrawingRevisionFile)

    base = (
        db.query(Drawing, Product, DrawingRevision, drawing_file)
        .join(Product, Product.drawing_id == Drawing.drawing_id)
        .outerjoin(DrawingRevision, DrawingRevision.revision_id == Drawing.current_revision_id)
        .outerjoin(
            drawing_file,
            and_(
                drawing_file.revision_id == Drawing.current_revision_id,
                drawing_file.file_kind == "DRAWING",
            ),
        )
        .filter(Drawing.is_active == True)
        .filter(Product.is_active == True)
        .filter(
            or_(
                Drawing.current_revision_id.is_(None),
                drawing_file.revision_file_id.is_(None),
            )
        )
    )

    if q:
        like = f"%{q.strip()}%"
        base = base.filter(
            or_(
                Drawing.drawing_no.ilike(like),
                Product.product_code.ilike(like),
                Product.product_name.ilike(like),
            )
        )

    total = base.with_entities(func.count()).scalar() or 0

    rows = (
        base.order_by(Drawing.created_at.desc(), Drawing.drawing_id.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )

    items = []
    for drawing, product, revision, file_row in rows:
        items.append(
            {
                "drawing_id": drawing.drawing_id,
                "drawing_no": drawing.drawing_no,
                "current_revision_id": drawing.current_revision_id,
                "current_revision_no": revision.rev_no if revision else None,
                "product_id": product.product_id,
                "product_code": product.product_code,
                "product_name": product.product_name,
                "status_text": "리비전 없음" if revision is None else "도면파일 없음",
                "created_at": drawing.created_at,
                "updated_at": drawing.updated_at,
            }
        )

    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
    }


@router.get("/{drawing_id}", response_model=DrawingOut)
def get_drawing(
    drawing_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    return drawing_crud.get_or_404(db, drawing_id, active_only=True)


@router.get("", response_model=DrawingListOut)
def list_drawings(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    q: str | None = Query(None),
    is_active: bool | None = Query(True),
    db: Session = Depends(get_db),
):
    base = (
        db.query(Drawing)
        .options(selectinload(Drawing.current_revision))
    )

    if is_active is not None:
        base = base.filter(Drawing.is_active == is_active)

    if q:
        like = f"%{q}%"
        base = base.filter(Drawing.drawing_no.ilike(like))

    total = base.count()

    items = (
        base.order_by(*_drawing_no_order())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )

    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
    }


@router.patch("/{drawing_id}", response_model=DrawingOut)
def update_drawing(
    drawing_id: int = Path(..., ge=1),
    payload: DrawingUpdate = None,
    db: Session = Depends(get_db),
):
    obj = drawing_crud.get_or_404(db, drawing_id, active_only=False)

    if payload.drawing_no is not None:
        obj.drawing_no = payload.drawing_no
    if payload.is_active is not None:
        obj.is_active = payload.is_active

    return drawing_crud.commit(db, obj)


@router.delete("/{drawing_id}", response_model=DrawingOut)
def delete_drawing(
    drawing_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    # 운영 안전상 도면은 soft delete
    return drawing_crud.soft_delete(db, drawing_id)
