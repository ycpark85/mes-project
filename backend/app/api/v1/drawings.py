from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import BigInteger, case, cast, desc, func, nullslast
from app.db.session import get_db
from app.models.drawing import Drawing
from app.schemas.drawing import DrawingCreate, DrawingUpdate, DrawingOut, DrawingListOut
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