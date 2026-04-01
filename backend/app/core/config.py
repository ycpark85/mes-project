from typing import Set

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="forbid",
    )

    app_env: str = "dev"
    database_url: str

    DRAWING_STORAGE_ROOT: str = Field(default=r"C:\mes_storage")
    DRAWING_MAX_MB: int = Field(default=50, ge=1, le=500)
    DRAWING_ALLOWED_EXT: Set[str] = Field(default_factory=set)

    DEFECT_PHOTO_STORAGE_ROOT: str = Field(default=r"C:\mes_storage")
    DEFECT_PHOTO_MAX_MB: int = Field(default=20, ge=1, le=500)
    DEFECT_PHOTO_ALLOWED_EXT: Set[str] = Field(default_factory=set)

    @field_validator("DRAWING_ALLOWED_EXT", "DEFECT_PHOTO_ALLOWED_EXT", mode="before")
    @classmethod
    def _normalize_allowed_ext(cls, v):
        if isinstance(v, (list, set, tuple)):
            return {str(x).strip().lower() for x in v if str(x).strip()}
        return v


settings = Settings()