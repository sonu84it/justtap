from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    demo_mode: bool


class GenerateResponse(BaseModel):
    style: str
    prompt: str
    message: str
    original_image_url: str
    result_image_url: str
    output_filename: str
    content_type: str
    storage_mode: str
