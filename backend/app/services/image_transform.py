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
    provider: str
    model_name: str
    aspect_ratio: str


class DemoTransformService:
    def transform(
        self,
        *,
        image_bytes: bytes | None,
        prompt: str,
        style: str,
        filename: str | None,
        content_type: str | None,
        mode: str,
    ) -> TransformResult:
        if image_bytes is None:
            raise NotImplementedError("Demo mode only supports uploaded-image transformations.")

        return TransformResult(
            content=image_bytes,
            content_type=content_type or "image/png",
            filename=f"{style}-{filename or 'result.png'}",
            message="Demo mode is enabled, so the uploaded image was returned unchanged.",
            provider="demo",
            model_name="demo-mode",
            aspect_ratio="source",
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

    def transform(
        self,
        *,
        image_bytes: bytes | None,
        prompt: str,
        style: str,
        filename: str | None,
        content_type: str | None,
        mode: str,
        aspect_ratio: str,
    ) -> TransformResult:
        if image_bytes is None or content_type is None:
            raise ValueError("Preserve mode requires an uploaded image.")

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
        base_name = os.path.splitext(filename or style)[0] or style

        return TransformResult(
            content=result_bytes,
            content_type=self.settings.vertex_output_mime_type or prepared_content_type,
            filename=f"{style}-{base_name}{output_extension}",
            message="Transformation complete with Imagen.",
            provider="imagen",
            model_name=self.settings.vertex_model,
            aspect_ratio="source",
        )


class GeminiFlashImageService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client

        try:
            from google import genai
        except ImportError as error:
            raise RuntimeError(
                "Gemini image dependencies are not installed. Add google-genai to requirements."
            ) from error

        if not self.settings.google_cloud_project:
            raise RuntimeError("GOOGLE_CLOUD_PROJECT must be set to use Gemini image generation.")

        self._client = genai.Client(
            vertexai=True,
            project=self.settings.google_cloud_project,
            location=self.settings.gemini_location,
        )
        return self._client

    def _extract_image(self, response) -> tuple[bytes, str]:
        candidates = getattr(response, "candidates", None) or []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            parts = getattr(content, "parts", None) or []
            for part in parts:
                inline_data = getattr(part, "inline_data", None)
                if inline_data and getattr(inline_data, "data", None):
                    mime_type = getattr(inline_data, "mime_type", None) or self.settings.gemini_output_mime_type
                    return inline_data.data, mime_type

        raise RuntimeError("Gemini returned no image data.")

    def _extract_text(self, response) -> str:
        candidates = getattr(response, "candidates", None) or []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            parts = getattr(content, "parts", None) or []
            for part in parts:
                text = getattr(part, "text", None)
                if text:
                    return text.strip()

        return ""

    def transform(
        self,
        *,
        image_bytes: bytes | None,
        prompt: str,
        style: str,
        filename: str | None,
        content_type: str | None,
        mode: str,
        aspect_ratio: str,
    ) -> TransformResult:
        try:
            from google.genai.types import GenerateContentConfig, ImageConfig, Modality, Part
        except ImportError as error:
            raise RuntimeError(
                "Gemini image dependencies are not installed. Add google-genai to requirements."
            ) from error

        client = self._get_client()
        contents = [prompt]
        if image_bytes is not None:
            contents.insert(0, Part.from_bytes(data=image_bytes, mime_type=content_type or "image/png"))

        response = client.models.generate_content(
            model=self.settings.gemini_model,
            contents=contents,
            config=GenerateContentConfig(
                response_modalities=[Modality.TEXT, Modality.IMAGE],
                image_config=ImageConfig(aspect_ratio=aspect_ratio),
                temperature=self.settings.gemini_temperature,
            ),
        )

        result_bytes, mime_type = self._extract_image(response)
        output_extension = ".png" if mime_type == "image/png" else ".jpg"
        base_name = os.path.splitext(filename or style or "result")[0] or "result"
        response_text = self._extract_text(response)
        message = response_text or (
            "Creative generation complete with Gemini."
            if mode == "creative"
            else "Transformation complete with Gemini."
        )

        return TransformResult(
            content=result_bytes,
            content_type=mime_type,
            filename=f"{style}-{base_name}{output_extension}",
            message=message,
            provider="gemini",
            model_name=self.settings.gemini_model,
            aspect_ratio=aspect_ratio,
        )


class RoutedTransformService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.imagen_service = VertexAITransformService(settings) if settings.vertex_enabled else None
        self.gemini_service = GeminiFlashImageService(settings) if settings.gemini_enabled else None

    def transform(
        self,
        *,
        image_bytes: bytes | None,
        prompt: str,
        style: str,
        filename: str | None,
        content_type: str | None,
        mode: str,
        aspect_ratio: str,
    ) -> TransformResult:
        if mode == "creative":
            if self.gemini_service is None:
                raise RuntimeError("Gemini creative mode is not enabled.")
            return self.gemini_service.transform(
                image_bytes=image_bytes,
                prompt=prompt,
                style=style,
                filename=filename,
                content_type=content_type,
                mode=mode,
                aspect_ratio=aspect_ratio,
            )

        if self.imagen_service is None:
            raise RuntimeError("Imagen preserve mode is not enabled.")
        return self.imagen_service.transform(
            image_bytes=image_bytes,
            prompt=prompt,
            style=style,
            filename=filename,
            content_type=content_type,
            mode=mode,
            aspect_ratio=aspect_ratio,
        )


def get_transform_service(settings: Settings):
    if settings.demo_mode:
        return DemoTransformService()

    if settings.vertex_enabled or settings.gemini_enabled:
        return RoutedTransformService(settings)

    return DemoTransformService()
