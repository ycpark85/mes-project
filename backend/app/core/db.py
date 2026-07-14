from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, settings
from app.core.observability import register_slow_query_logging
from app.db.base import Base


def build_engine_kwargs(
    database_url: str,
    app_settings: Settings,
) -> dict:
    kwargs: dict = {"pool_pre_ping": True}

    if make_url(database_url).get_backend_name() != "postgresql":
        return kwargs

    statement_timeout_ms = app_settings.DB_STATEMENT_TIMEOUT_SECONDS * 1000
    lock_timeout_ms = app_settings.DB_LOCK_TIMEOUT_SECONDS * 1000
    idle_transaction_timeout_ms = (
        app_settings.DB_IDLE_TRANSACTION_TIMEOUT_SECONDS * 1000
    )
    kwargs.update(
        pool_size=app_settings.DB_POOL_SIZE,
        max_overflow=app_settings.DB_MAX_OVERFLOW,
        pool_timeout=app_settings.DB_POOL_TIMEOUT_SECONDS,
        pool_recycle=app_settings.DB_POOL_RECYCLE_SECONDS,
        connect_args={
            "connect_timeout": app_settings.DB_CONNECT_TIMEOUT_SECONDS,
            "application_name": app_settings.DB_APPLICATION_NAME,
            "options": (
                f"-c statement_timeout={statement_timeout_ms} "
                f"-c lock_timeout={lock_timeout_ms} "
                f"-c idle_in_transaction_session_timeout={idle_transaction_timeout_ms}"
            ),
        },
    )
    return kwargs


engine = create_engine(
    settings.database_url,
    **build_engine_kwargs(settings.database_url, settings),
)
register_slow_query_logging(engine, settings.SLOW_QUERY_THRESHOLD_MS)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def set_local_statement_timeout(
    db: Session,
    timeout_seconds: int | None = None,
) -> None:
    if db.get_bind().dialect.name != "postgresql":
        return

    timeout_ms = (
        timeout_seconds or settings.DB_BULK_STATEMENT_TIMEOUT_SECONDS
    ) * 1000
    db.execute(
        text("SELECT set_config('statement_timeout', :timeout, true)"),
        {"timeout": f"{timeout_ms}ms"},
    )

def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        if db.in_transaction():
            db.rollback()
        raise
    finally:
        db.close()
