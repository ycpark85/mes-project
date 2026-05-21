from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.router import router as v1_router
from app.core.db import SessionLocal, engine
from app.services.auth_seed import ensure_auth_seed_data


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup 영역
    # DB 연결 체크 (실패 시 서버 자체가 안 뜸)
    with engine.connect() as conn:
        pass

    # 인증/권한 기본 seed
    db = SessionLocal()
    try:
        ensure_auth_seed_data(db)
    finally:
        db.close()

    yield

    # shutdown 영역
    # 지금은 정리할 자원 없음 (나중에 캐시, 메시지큐 등)
    pass


app = FastAPI(
    title="MES API",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(v1_router, prefix="/api/v1")