from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import Set


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

    @field_validator("DRAWING_ALLOWED_EXT", mode="before")
    @classmethod
    def _parse_allowed_ext(cls, v):
        if isinstance(v, str):
            return {x.strip().lower() for x in v.split(",") if x.strip()}
        if isinstance(v, (list, set)):
            return {str(x).strip().lower() for x in v}
        return set()
    
    DEFECT_PHOTO_ALLOWED_EXT: Set[str] = Field(default_factory=set)

    @field_validator("DEFECT_PHOTO_ALLOWED_EXT", mode="before")
    @classmethod
    def _parse_defect_photo_allowed_ext(cls, v):
        if isinstance(v, str):
            return {x.strip().lower() for x in v.split(",") if x.strip()}
        if isinstance(v, (list, set)):
            return {str(x).strip().lower() for x in v}
        return set()


settings = Settings()