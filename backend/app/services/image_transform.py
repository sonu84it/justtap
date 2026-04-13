import os
import tempfile
from dataclasses import dataclass
from io import BytesIO
import logging

from PIL import Image as PilImage

from app.config import Settings

logger = logging.getLogger(__name__)


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
        self._model = None

    def _get_model(self):
        if self._model is not None:
            return self._model

        try:
            import vertexai
            from vertexai.preview.vision_models import ImageGenerationModel
        except ImportError as error:
            raise RuntimeError(
                "Vertex AI dependencies are not installed. Add google-cloud-aiplatform to requirements."
            ) from error

        if not self.settings.google_cloud_project:
            raise RuntimeError("GOOGLE_CLOUD_PROJECT must be set to use Vertex AI image editing.")

        vertexai.init(
            project=self.settings.google_cloud_project,
            location=self.settings.vertex_location
        )
        self._model = ImageGenerationModel.from_pretrained(self.settings.vertex_model)
        return self._model

    def _prepare_base_image(self, image_bytes: bytes, content_type: str):
        from vertexai.preview.vision_models import Image

        if content_type in {"image/png", "image/jpeg"}:
            return Image(image_bytes=image_bytes), content_type

        with PilImage.open(BytesIO(image_bytes)) as source_image:
            converted = source_image.convert("RGBA")
            buffer = BytesIO()
            converted.save(buffer, format="PNG")
            return Image(image_bytes=buffer.getvalue()), "image/png"

    def _read_generated_bytes(self, generated_image, output_mime_type: str) -> bytes:
        suffix = ".png" if output_mime_type == "image/png" else ".jpg"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            generated_image.save(location=temp_path, include_generation_parameters=False)
            with open(temp_path, "rb") as saved_image:
                return saved_image.read()
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def _resolve_guidance_scale(self, style: str) -> float:
        return self.settings.vertex_guidance_scales.get(style, self.settings.vertex_guidance_scale)

    def transform(self, *, image_bytes: bytes, prompt: str, style: str, filename: str, content_type: str) -> TransformResult:
        from vertexai.preview.vision_models import RawReferenceImage

        model = self._get_model()
        base_image, prepared_content_type = self._prepare_base_image(image_bytes, content_type)
        guidance_scale = self._resolve_guidance_scale(style)
        reference_images = [
            RawReferenceImage(
                reference_id=0,
                image=base_image
            )
        ]

        logger.info(
            "Vertex image transform requested",
            extra={
                "style": style,
                "guidance_scale": guidance_scale,
                "model_name": self.settings.vertex_model,
            }
        )

        response = model.edit_image(
            base_image=base_image,
            reference_images=reference_images,
            prompt=prompt,
            negative_prompt=self.settings.vertex_negative_prompt,
            number_of_images=1,
            guidance_scale=guidance_scale,
            output_mime_type=self.settings.vertex_output_mime_type,
            safety_filter_level=self.settings.vertex_safety_filter_level,
            person_generation=self.settings.vertex_person_generation
        )

        if not response:
            raise RuntimeError("Vertex AI returned no edited images.")

        result_bytes = self._read_generated_bytes(response[0], self.settings.vertex_output_mime_type)
        output_extension = ".png" if self.settings.vertex_output_mime_type == "image/png" else ".jpg"
        base_name = os.path.splitext(filename)[0] or style

        return TransformResult(
            content=result_bytes,
            content_type=self.settings.vertex_output_mime_type or prepared_content_type,
            filename=f"{style}-{base_name}{output_extension}",
            message="Transformation complete with Vertex AI."
        )


def get_transform_service(settings: Settings):
    if settings.demo_mode:
        return DemoTransformService()

    if settings.vertex_enabled:
        return VertexAITransformService(settings)

    return DemoTransformService()
