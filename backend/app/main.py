from pathlib import Path
from urllib.parse import quote
from io import BytesIO

from fastapi import FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, UnidentifiedImageError

from app.config import get_settings
from app.models import GenerateResponse, HealthResponse
from app.prompts import get_style_prompt
from app.services.image_transform import get_transform_service
from app.services.storage import StorageService
from app.services.usage_limits import DailyUsageLimiter

settings = get_settings()
app = FastAPI(title=settings.app_name)

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


def validate_image_dimensions(payload: bytes) -> None:
    try:
        with Image.open(BytesIO(payload)) as image:
            width, height = image.size
    except UnidentifiedImageError as error:
        raise HTTPException(status_code=400, detail="The uploaded file is not a supported image.") from error

    megapixels = (width * height) / 1_000_000
    if width > settings.max_image_width or height > settings.max_image_height:
        raise HTTPException(
            status_code=413,
            detail=(
                f"Image dimensions are too large. Maximum allowed size is "
                f"{settings.max_image_width}x{settings.max_image_height} pixels."
            )
        )

    if megapixels > settings.max_image_megapixels:
        raise HTTPException(
            status_code=413,
            detail=(
                f"Image resolution is too high. Maximum allowed resolution is "
                f"{settings.max_image_megapixels} megapixels."
            )
        )


@app.post("/generate", response_model=GenerateResponse)
async def generate_image(request: Request, file: UploadFile = File(...), style: str = Form(...)) -> GenerateResponse:
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Please upload a valid image file.")

    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(payload) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File is too large. The limit is {settings.max_upload_size_mb} MB."
        )

    validate_image_dimensions(payload)

    try:
        prompt = get_style_prompt(style)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    usage_decision = usage_limiter.consume(get_client_identifier(request))
    if not usage_decision.allowed:
        raise HTTPException(
            status_code=429,
            detail=(
                f"Daily limit reached. You can generate up to {usage_decision.daily_limit} "
                "images per day without signing in."
            )
        )

    original_asset = storage_service.save_bytes(
        payload,
        original_filename=file.filename or "upload.png",
        content_type=file.content_type,
        prefix=settings.upload_prefix
    )

    try:
        transform_result = transform_service.transform(
            image_bytes=payload,
            prompt=prompt,
            style=style,
            filename=file.filename or "upload.png",
            content_type=file.content_type
        )
    except NotImplementedError as error:
        raise HTTPException(status_code=501, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Transformation failed: {error}") from error

    result_asset = storage_service.save_bytes(
        transform_result.content,
        original_filename=transform_result.filename,
        content_type=transform_result.content_type,
        prefix=settings.result_prefix
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
