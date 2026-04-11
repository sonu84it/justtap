import base64
import mimetypes
import os
import uuid
from dataclasses import dataclass

from google.cloud import storage

from app.config import Settings


@dataclass
class StoredAsset:
    path: str
    url: str | None
    content_type: str
    storage_mode: str


class StorageService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.bucket_name = settings.gcs_bucket_name
        self.client = storage.Client(project=settings.google_cloud_project) if self.bucket_name else None

    def _guess_extension(self, filename: str, content_type: str) -> str:
        extension = os.path.splitext(filename)[1]
        if extension:
            return extension
        guessed = mimetypes.guess_extension(content_type or "")
        return guessed or ".bin"

    def save_bytes(self, payload: bytes, *, original_filename: str, content_type: str, prefix: str) -> StoredAsset:
        extension = self._guess_extension(original_filename, content_type)
        blob_name = f"{prefix}/{uuid.uuid4().hex}{extension}"

        if not self.bucket_name:
            encoded = base64.b64encode(payload).decode("utf-8")
            return StoredAsset(
                path=blob_name,
                url=f"data:{content_type};base64,{encoded}",
                content_type=content_type,
                storage_mode="inline"
            )

        bucket = self.client.bucket(self.bucket_name)
        blob = bucket.blob(blob_name)
        blob.upload_from_string(payload, content_type=content_type)
        return StoredAsset(
            path=blob_name,
            url=None,
            content_type=content_type,
            storage_mode="gcs"
        )

    def read_bytes(self, asset_path: str) -> tuple[bytes, str]:
        if not self.bucket_name:
            raise FileNotFoundError("Inline assets are returned directly and are not stored on the server.")

        bucket = self.client.bucket(self.bucket_name)
        blob = bucket.blob(asset_path)
        if not blob.exists():
            raise FileNotFoundError(f"Asset not found: {asset_path}")

        payload = blob.download_as_bytes()
        content_type = blob.content_type or mimetypes.guess_type(asset_path)[0] or "application/octet-stream"
        return payload, content_type
