from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Magic Image Studio API"
    app_env: str = "development"
    demo_mode: bool = True
    daily_generation_limit: int = 10
    frontend_dist_dir: str = str(Path(__file__).resolve().parents[2] / "frontend" / "dist")
    upload_prefix: str = "uploads"
    result_prefix: str = "results"
    max_upload_size_mb: int = 5
    max_image_width: int = 2048
    max_image_height: int = 2048
    max_image_megapixels: int = 12
    allowed_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:4173",
            "http://127.0.0.1:4173"
        ]
    )
    gcs_bucket_name: str | None = None
    gcs_public_base_url: str | None = None
    google_cloud_project: str | None = None
    vertex_enabled: bool = False
    vertex_location: str = "us-central1"
    vertex_model: str = "imagen-3.0-capability-001"
    vertex_output_mime_type: str = "image/png"
    vertex_guidance_scale: float = 18.0
    vertex_guidance_scales: dict[str, float] = Field(
        default_factory=lambda: {
            "cinematic": 15.0,
            "magic": 16.0,
            "viral": 18.0,
            "fantasy": 19.0,
            "meme": 19.0,
        }
    )
    vertex_negative_prompt: str = (
        "blurry, distorted, low quality, extra limbs, duplicated features, warped face, "
        "unreadable text, watermark, logo, frame"
    )
    vertex_safety_filter_level: str = "block_some"
    vertex_person_generation: str = "allow_adult"
    gemini_enabled: bool = False
    gemini_location: str = "global"
    gemini_model: str = "gemini-2.5-flash-image"
    gemini_output_mime_type: str = "image/png"
    gemini_temperature: float = 1.0
    gemini_aspect_ratio: str = "1:1"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
