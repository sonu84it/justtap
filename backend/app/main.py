from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.models import GenerateResponse, HealthResponse
from app.prompts import get_style_prompt
from app.services.image_transform import get_transform_service
from app.services.storage import StorageService

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


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(status="ok", demo_mode=settings.demo_mode)


def build_asset_url(request: Request, asset_path: str, inline_url: str | None, storage_mode: str) -> str:
    if storage_mode == "inline" and inline_url:
        return inline_url

    base_url = str(request.base_url).rstrip("/")
    return f"{base_url}/files/{quote(asset_path, safe='/')}"


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

    try:
        prompt = get_style_prompt(style)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

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
        storage_mode=result_asset.storage_mode
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
