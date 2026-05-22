from typing import Set

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_AUTH_SECRET_KEY = "mes-dev-auth-secret-key-change-me"
PRODUCTION_ENVS = {"prod", "production"}

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="forbid",
    )

    app_env: str = "dev"
    database_url: str

    AUTH_SECRET_KEY: str = Field(default="mes-dev-auth-secret-key-change-me")
    AUTH_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=720, ge=1, le=1440)
    MES_ADMIN_LOGIN_ID: str = Field(default="admin")
    MES_ADMIN_PASSWORD: str | None = Field(default=None)
    
    BACKEND_ALLOWED_HOSTS: Set[str] = Field(default_factory=set)

    DRAWING_STORAGE_ROOT: str = Field(default=r"C:\mes_storage")
    DRAWING_MAX_MB: int = Field(default=50, ge=1, le=500)
    DRAWING_ALLOWED_EXT: Set[str] = Field(default_factory=set)

    DEFECT_PHOTO_STORAGE_ROOT: str = Field(default=r"C:\mes_storage")
    DEFECT_PHOTO_MAX_MB: int = Field(default=20, ge=1, le=500)
    DEFECT_PHOTO_ALLOWED_EXT: Set[str] = Field(default_factory=set)

    PLATE_DATA_STORAGE_ROOT: str = Field(default=r"C:\mes_storage")
    PLATE_DATA_MAX_MB: int = Field(default=100, ge=1, le=1000)
    PLATE_DATA_ALLOWED_EXT: Set[str] = Field(default_factory=set)

    @field_validator("DRAWING_ALLOWED_EXT", "DEFECT_PHOTO_ALLOWED_EXT","PLATE_DATA_ALLOWED_EXT", mode="before")
    @classmethod
    def _normalize_allowed_ext(cls, v):
        if isinstance(v, (list, set, tuple)):
            return {str(x).strip().lower() for x in v if str(x).strip()}
        return v


settings = Settings()

def is_production_env() -> bool:
    return settings.app_env.strip().lower() in PRODUCTION_ENVS


def validate_runtime_settings() -> None:
    if not is_production_env():
        return

    secret_key = settings.AUTH_SECRET_KEY.strip()

    if secret_key == DEFAULT_AUTH_SECRET_KEY or len(secret_key) < 32:
        raise RuntimeError(
            "운영 환경에서는 AUTH_SECRET_KEY를 32자 이상의 안전한 값으로 설정해야 합니다."
        )

    if not settings.BACKEND_ALLOWED_HOSTS:
        raise RuntimeError(
            "운영 환경에서는 BACKEND_ALLOWED_HOSTS를 설정해야 합니다."
        )