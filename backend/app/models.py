from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    demo_mode: bool
    daily_generation_limit: int


class GenerateResponse(BaseModel):
    style: str
    prompt: str
    message: str
    original_image_url: str
    result_image_url: str
    output_filename: str
    content_type: str
    storage_mode: str
    daily_limit: int
    used_today: int
    remaining_generations: int
