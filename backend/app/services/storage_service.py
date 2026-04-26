from __future__ import annotations

import os
import uuid
from abc import ABC, abstractmethod
from pathlib import Path

from app.config import settings

STORAGE_DIR = Path(__file__).resolve().parent.parent.parent / "storage" / "images"


class StorageBackend(ABC):
    @abstractmethod
    async def upload(self, data: bytes, path: str, content_type: str = "image/jpeg") -> str:
        ...

    @abstractmethod
    async def delete(self, path: str) -> None:
        ...

    @abstractmethod
    async def get_url(self, path: str) -> str:
        ...


class LocalStorageBackend(StorageBackend):
    async def upload(self, data: bytes, path: str, content_type: str = "image/jpeg") -> str:
        full_path = STORAGE_DIR / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(data)
        return f"/static/images/{path}"

    async def delete(self, path: str) -> None:
        full_path = STORAGE_DIR / path
        if full_path.exists():
            full_path.unlink()

    async def get_url(self, path: str) -> str:
        return f"/static/images/{path}"


class MinIOStorageBackend(StorageBackend):
    def __init__(self):
        import boto3
        self._client = boto3.client(
            "s3",
            endpoint_url=f"http://{settings.MINIO_ENDPOINT}",
            aws_access_key_id=settings.MINIO_ACCESS_KEY,
            aws_secret_access_key=settings.MINIO_SECRET_KEY,
        )
        self._bucket = settings.MINIO_BUCKET
        self._ensure_bucket()

    def _ensure_bucket(self):
        try:
            self._client.head_bucket(Bucket=self._bucket)
        except Exception:
            self._client.create_bucket(Bucket=self._bucket)

    async def upload(self, data: bytes, path: str, content_type: str = "image/jpeg") -> str:
        import io
        self._client.upload_fileobj(io.BytesIO(data), self._bucket, path, ExtraArgs={"ContentType": content_type})
        return self._client.generate_presigned_url("get_object", Params={"Bucket": self._bucket, "Key": path})

    async def delete(self, path: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=path)

    async def get_url(self, path: str) -> str:
        return self._client.generate_presigned_url("get_object", Params={"Bucket": self._bucket, "Key": path})


def get_storage() -> StorageBackend:
    if settings.STORAGE_BACKEND == "minio":
        return MinIOStorageBackend()
    return LocalStorageBackend()


def generate_storage_path(device_id: str, date_str: str, filename: str) -> str:
    return f"{device_id}/{date_str}/{filename}"
