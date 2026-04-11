from dataclasses import dataclass

from app.config import Settings


@dataclass
class TransformResult:
    content: bytes
    content_type: str
    filename: str
    message: str


class DemoTransformService:
    def transform(self, *, image_bytes: bytes, prompt: str, style: str, filename: str, content_type: str) -> TransformResult:
        return TransformResult(
            content=image_bytes,
            content_type=content_type,
            filename=f"{style}-{filename}",
            message="Demo mode is enabled, so the uploaded image was returned unchanged."
        )


class VertexAITransformService:
    def __init__(self, settings: Settings):
        self.settings = settings

    def transform(self, *, image_bytes: bytes, prompt: str, style: str, filename: str, content_type: str) -> TransformResult:
        raise NotImplementedError(
            "Vertex AI image editing is not wired in yet. Replace this method with a live implementation when ready."
        )


def get_transform_service(settings: Settings):
    if settings.demo_mode:
        return DemoTransformService()

    if settings.vertex_enabled:
        return VertexAITransformService(settings)

    return DemoTransformService()
