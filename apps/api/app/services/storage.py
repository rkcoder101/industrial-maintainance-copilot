import os
from pathlib import Path
from typing import BinaryIO, Protocol
from uuid import UUID, uuid4

from app.services.ingestion_errors import StorageOperationError


class StorageBackend(Protocol):
    async def save(self, temp_path: Path, storage_key: str) -> str: ...

    async def delete(self, storage_key: str) -> None: ...

    async def exists(self, storage_key: str) -> bool: ...

    async def open(self, storage_key: str) -> BinaryIO: ...


class LocalStorageBackend:
    def __init__(self, upload_root: Path) -> None:
        self.upload_root = upload_root.expanduser().resolve()
        self.temp_root = self.upload_root / ".tmp"
        self.ensure_root()

    def ensure_root(self) -> None:
        self.upload_root.mkdir(parents=True, exist_ok=True, mode=0o750)
        self.temp_root.mkdir(parents=True, exist_ok=True, mode=0o750)

    def make_storage_key(self, *, document_id: UUID, extension: str) -> str:
        safe_extension = extension.lower()
        if not safe_extension.startswith(".") or "/" in safe_extension or "\\" in safe_extension:
            raise StorageOperationError()
        generated_name = f"{uuid4()}{safe_extension}"
        return f"{document_id.hex[:4]}/{document_id}/{generated_name}"

    def make_page_image_key(
        self, *, document_id: UUID, page_number: int, extension: str = ".png"
    ) -> str:
        safe_extension = extension.lower()
        if not safe_extension.startswith(".") or "/" in safe_extension or "\\" in safe_extension:
            raise StorageOperationError()
        return (
            f"{document_id.hex[:4]}/{document_id}/page-{page_number:04d}-{uuid4()}{safe_extension}"
        )

    def resolve_key(self, storage_key: str) -> Path:
        if "\x00" in storage_key or storage_key.startswith(("/", "\\")):
            raise StorageOperationError()
        candidate = (self.upload_root / storage_key).resolve()
        if not candidate.is_relative_to(self.upload_root):
            raise StorageOperationError()
        return candidate

    async def save(self, temp_path: Path, storage_key: str) -> str:
        destination = self.resolve_key(storage_key)
        try:
            destination.parent.mkdir(parents=True, exist_ok=True, mode=0o750)
            os.replace(temp_path, destination)
            return storage_key
        except OSError as exc:
            raise StorageOperationError() from exc

    async def delete(self, storage_key: str) -> None:
        path = self.resolve_key(storage_key)
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            raise StorageOperationError() from exc

    async def exists(self, storage_key: str) -> bool:
        return self.resolve_key(storage_key).is_file()

    async def open(self, storage_key: str) -> BinaryIO:
        try:
            return self.resolve_key(storage_key).open("rb")
        except OSError as exc:
            raise StorageOperationError() from exc


class DocumentStorageService:
    def __init__(self, backend: StorageBackend) -> None:
        self.backend = backend

    def make_storage_key(self, *, document_id: UUID, extension: str) -> str:
        if not isinstance(self.backend, LocalStorageBackend):
            return f"{document_id}/{uuid4()}{extension.lower()}"
        return self.backend.make_storage_key(document_id=document_id, extension=extension)

    async def finalize(self, *, temp_path: Path, storage_key: str) -> str:
        return await self.backend.save(temp_path, storage_key)

    async def delete(self, storage_key: str | None) -> None:
        if storage_key:
            await self.backend.delete(storage_key)


class RenderedPageStorageService(DocumentStorageService):
    def make_page_image_key(self, *, document_id: UUID, page_number: int) -> str:
        if isinstance(self.backend, LocalStorageBackend):
            return self.backend.make_page_image_key(
                document_id=document_id,
                page_number=page_number,
            )
        return f"{document_id}/page-{page_number:04d}-{uuid4()}.png"
