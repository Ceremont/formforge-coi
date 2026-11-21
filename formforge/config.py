from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="FORMFORGE_", extra="ignore")
    max_upload_mb: int = Field(default=20, ge=1, le=100)
    processing_timeout: int = Field(default=90, ge=1, le=300)
    max_pages: int = Field(default=30, ge=1, le=100)
    max_cells: int = Field(default=30_000, ge=100, le=200_000)
    max_blocks: int = Field(default=12_000, ge=100, le=50_000)
    max_uncompressed_mb: int = Field(default=80, ge=1, le=200)
    max_image_pixels: int = Field(default=25_000_000, ge=100_000, le=50_000_000)
    worker_memory_mb: int = Field(default=768, ge=256, le=2048)
    max_workers: int = Field(default=2, ge=1, le=8)
    ocr_languages: str = "pol+eng"
    ocr_timeout: int = Field(default=25, ge=1, le=120)
    ocr_variants: int = Field(default=3, ge=1, le=3)
    analysis_mode: Literal["deterministic", "local-ai-assisted"] = "deterministic"
    local_model_path: str = ""
    dictionary_registry_path: str = ""
    export_format: Literal["official", "preview"] = "official"
    auth_enabled: bool = False
    jwt_secret: str = ""
    jwt_issuer: str = "formforge"
    jwt_audience: str = "formforge-api"

    @model_validator(mode="after")
    def check_auth(self):
        if self.auth_enabled and len(self.jwt_secret) < 32:
            raise ValueError("JWT secret must have at least 32 characters when authentication is enabled")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
