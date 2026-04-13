import json
import logging
import time
from io import BytesIO
from pathlib import Path
from urllib.parse import quote
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageOps, UnidentifiedImageError

from app.config import get_settings
from app.models import GenerateResponse, HealthResponse
from app.prompts import get_style_prompt
from app.services.image_transform import get_transform_service
from app.services.storage import StorageService
from app.services.usage_limits import DailyUsageLimiter

settings = get_settings()
app = FastAPI(title=settings.app_name)
logger = logging.getLogger("magic_image_studio.usage")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

storage_service = StorageService(settings)
transform_service = get_transform_service(settings)
usage_limiter = DailyUsageLimiter(settings)


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        demo_mode=settings.demo_mode,
        daily_generation_limit=settings.daily_generation_limit
    )


def build_asset_url(request: Request, asset_path: str, inline_url: str | None, storage_mode: str) -> str:
    if storage_mode == "inline" and inline_url:
        return inline_url

    base_url = str(request.base_url).rstrip("/")
    return f"{base_url}/files/{quote(asset_path, safe='/')}"


def get_client_identifier(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    if request.client and request.client.host:
        return request.client.host

    return "anonymous"


def normalize_uploaded_image(payload: bytes, content_type: str | None) -> tuple[bytes, str, int, int, int, int]:
    try:
        with Image.open(BytesIO(payload)) as source_image:
            image = ImageOps.exif_transpose(source_image)
            original_width, original_height = image.size
    except UnidentifiedImageError as error:
        raise HTTPException(status_code=400, detail="The uploaded file is not a supported image.") from error

    width, height = original_width, original_height
    megapixels = (width * height) / 1_000_000
    exceeds_dimension_limit = width > settings.max_image_width or height > settings.max_image_height
    exceeds_megapixel_limit = megapixels > settings.max_image_megapixels

    if exceeds_dimension_limit or exceeds_megapixel_limit:
        resize_ratio = min(
            settings.max_image_width / width,
            settings.max_image_height / height,
            (settings.max_image_megapixels / megapixels) ** 0.5 if megapixels > 0 else 1.0,
            1.0
        )
        resized_width = max(1, int(width * resize_ratio))
        resized_height = max(1, int(height * resize_ratio))
        image.thumbnail((resized_width, resized_height), Image.Resampling.LANCZOS)
        width, height = image.size

        while (width * height) / 1_000_000 > settings.max_image_megapixels:
            width = max(1, int(width * 0.95))
            height = max(1, int(height * 0.95))
            image = image.resize((width, height), Image.Resampling.LANCZOS)

        output_content_type = content_type or "image/jpeg"
        output_format = "JPEG"

        if output_content_type == "image/png":
            output_format = "PNG"
        elif output_content_type == "image/webp":
            output_format = "WEBP"
        else:
            if image.mode not in {"RGB", "L"}:
                image = image.convert("RGB")
            output_content_type = "image/jpeg"

        buffer = BytesIO()
        save_kwargs = {"format": output_format}
        if output_format == "JPEG":
            save_kwargs.update({"quality": 92, "optimize": True})
        elif output_format == "WEBP":
            save_kwargs.update({"quality": 92, "method": 6})
        image.save(buffer, **save_kwargs)
        return buffer.getvalue(), output_content_type, original_width, original_height, width, height

    return payload, content_type or "image/jpeg", original_width, original_height, width, height


def log_usage_event(event: dict) -> None:
    logger.info(json.dumps(event, default=str))


def resolve_guidance_scale(style: str) -> float:
    return settings.vertex_guidance_scales.get(style, settings.vertex_guidance_scale)


@app.post("/generate", response_model=GenerateResponse)
async def generate_image(request: Request, file: UploadFile = File(...), style: str = Form(...)) -> GenerateResponse:
    request_id = uuid4().hex
    started_at = time.perf_counter()
    client_ip = get_client_identifier(request)
    guidance_scale = resolve_guidance_scale(style)
    base_event = {
        "event_type": "image_generation",
        "request_id": request_id,
        "client_ip": client_ip,
        "style_selected": style,
        "original_filename": file.filename or "upload.png",
        "content_type": file.content_type,
        "origin": request.headers.get("origin"),
        "user_agent": request.headers.get("user-agent"),
        "vertex_enabled": settings.vertex_enabled,
        "demo_mode": settings.demo_mode,
        "model_name": settings.vertex_model,
        "guidance_scale": guidance_scale,
    }

    if not file.content_type or not file.content_type.startswith("image/"):
        log_usage_event(
            {
                **base_event,
                "status": "failed",
                "error_message": "Please upload a valid image file.",
                "latency_ms": round((time.perf_counter() - started_at) * 1000, 2),
            }
        )
        raise HTTPException(status_code=400, detail="Please upload a valid image file.")

    payload = await file.read()
    if not payload:
        log_usage_event(
            {
                **base_event,
                "status": "failed",
                "file_size_bytes": 0,
                "error_message": "The uploaded file is empty.",
                "latency_ms": round((time.perf_counter() - started_at) * 1000, 2),
            }
        )
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(payload) > max_bytes:
        log_usage_event(
            {
                **base_event,
                "status": "failed",
                "file_size_bytes": len(payload),
                "error_message": f"File is too large. The limit is {settings.max_upload_size_mb} MB.",
                "latency_ms": round((time.perf_counter() - started_at) * 1000, 2),
            }
        )
        raise HTTPException(
            status_code=413,
            detail=f"File is too large. The limit is {settings.max_upload_size_mb} MB."
        )

    try:
        payload, content_type, original_width, original_height, width, height = normalize_uploaded_image(
            payload,
            file.content_type
        )
    except HTTPException as error:
        log_usage_event(
            {
                **base_event,
                "status": "failed",
                "file_size_bytes": len(payload),
                "error_message": error.detail,
                "latency_ms": round((time.perf_counter() - started_at) * 1000, 2),
            }
        )
        raise

    try:
        prompt = get_style_prompt(style)
    except ValueError as error:
        log_usage_event(
            {
                **base_event,
                "status": "failed",
                "file_size_bytes": len(payload),
                "original_image_width": original_width,
                "original_image_height": original_height,
                "image_width": width,
                "image_height": height,
                "error_message": str(error),
                "latency_ms": round((time.perf_counter() - started_at) * 1000, 2),
            }
        )
        raise HTTPException(status_code=400, detail=str(error)) from error

    usage_decision = usage_limiter.consume(client_ip)
    if not usage_decision.allowed:
        limit_message = (
            f"Daily limit reached. You can generate up to {usage_decision.daily_limit} "
            "images per day without signing in."
        )
        log_usage_event(
            {
                **base_event,
                "status": "blocked",
                "file_size_bytes": len(payload),
                "original_image_width": original_width,
                "original_image_height": original_height,
                "image_width": width,
                "image_height": height,
                "prompt": prompt,
                "used_today": usage_decision.used_today,
                "remaining_generations": usage_decision.remaining_generations,
                "daily_limit": usage_decision.daily_limit,
                "error_message": limit_message,
                "latency_ms": round((time.perf_counter() - started_at) * 1000, 2),
            }
        )
        raise HTTPException(
            status_code=429,
            detail=limit_message
        )

    original_asset = storage_service.save_bytes(
        payload,
        original_filename=file.filename or "upload.png",
        content_type=content_type,
        prefix=settings.upload_prefix
    )

    try:
        transform_result = transform_service.transform(
            image_bytes=payload,
            prompt=prompt,
            style=style,
            filename=file.filename or "upload.png",
            content_type=content_type
        )
    except NotImplementedError as error:
        log_usage_event(
            {
                **base_event,
                "status": "failed",
                "file_size_bytes": len(payload),
                "original_image_width": original_width,
                "original_image_height": original_height,
                "image_width": width,
                "image_height": height,
                "prompt": prompt,
                "used_today": usage_decision.used_today,
                "remaining_generations": usage_decision.remaining_generations,
                "daily_limit": usage_decision.daily_limit,
                "stored_input_path": original_asset.path,
                "error_message": str(error),
                "latency_ms": round((time.perf_counter() - started_at) * 1000, 2),
            }
        )
        raise HTTPException(status_code=501, detail=str(error)) from error
    except Exception as error:
        error_message = f"Transformation failed: {error}"
        log_usage_event(
            {
                **base_event,
                "status": "failed",
                "file_size_bytes": len(payload),
                "original_image_width": original_width,
                "original_image_height": original_height,
                "image_width": width,
                "image_height": height,
                "prompt": prompt,
                "used_today": usage_decision.used_today,
                "remaining_generations": usage_decision.remaining_generations,
                "daily_limit": usage_decision.daily_limit,
                "stored_input_path": original_asset.path,
                "error_message": error_message,
                "latency_ms": round((time.perf_counter() - started_at) * 1000, 2),
            }
        )
        raise HTTPException(status_code=500, detail=f"Transformation failed: {error}") from error

    result_asset = storage_service.save_bytes(
        transform_result.content,
        original_filename=transform_result.filename,
        content_type=transform_result.content_type,
        prefix=settings.result_prefix
    )

    log_usage_event(
        {
            **base_event,
            "status": "success",
            "file_size_bytes": len(payload),
            "original_image_width": original_width,
            "original_image_height": original_height,
            "image_width": width,
            "image_height": height,
            "prompt": prompt,
            "used_today": usage_decision.used_today,
            "remaining_generations": usage_decision.remaining_generations,
            "daily_limit": usage_decision.daily_limit,
            "stored_input_path": original_asset.path,
            "stored_output_path": result_asset.path,
            "output_filename": Path(result_asset.path).name,
            "output_content_type": result_asset.content_type,
            "storage_mode": result_asset.storage_mode,
            "latency_ms": round((time.perf_counter() - started_at) * 1000, 2),
        }
    )

    return GenerateResponse(
        style=style,
        prompt=prompt,
        message=transform_result.message,
        original_image_url=build_asset_url(request, original_asset.path, original_asset.url, original_asset.storage_mode),
        result_image_url=build_asset_url(request, result_asset.path, result_asset.url, result_asset.storage_mode),
        output_filename=Path(result_asset.path).name,
        content_type=result_asset.content_type,
        storage_mode=result_asset.storage_mode,
        daily_limit=usage_decision.daily_limit,
        used_today=usage_decision.used_today,
        remaining_generations=usage_decision.remaining_generations
    )


@app.get("/files/{asset_path:path}")
async def get_stored_file(asset_path: str) -> Response:
    try:
        payload, content_type = storage_service.read_bytes(asset_path)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Failed to fetch stored asset: {error}") from error

    return Response(content=payload, media_type=content_type)


frontend_dist = Path(settings.frontend_dist_dir)
assets_dir = frontend_dist / "assets"
index_file = frontend_dist / "index.html"

if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")


@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Route not found.")

    if index_file.exists():
        return FileResponse(index_file)

    return {
        "message": "Magic Image Studio backend is running.",
        "hint": "Build the frontend to let FastAPI serve the app shell."
    }
