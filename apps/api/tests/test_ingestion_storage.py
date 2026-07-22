from uuid import uuid4

import pytest

from app.services.ingestion_errors import StorageOperationError
from app.services.storage import DocumentStorageService, LocalStorageBackend
from tests.ingestion_helpers import assert_inside


@pytest.mark.anyio
async def test_local_storage_atomic_save_and_delete(tmp_path) -> None:
    backend = LocalStorageBackend(tmp_path / "uploads")
    storage = DocumentStorageService(backend)
    temp_path = backend.temp_root / "incoming.tmp"
    temp_path.write_bytes(b"payload")
    key = storage.make_storage_key(document_id=uuid4(), extension=".pdf")

    saved_key = await storage.finalize(temp_path=temp_path, storage_key=key)

    final_path = backend.resolve_key(saved_key)
    assert final_path.read_bytes() == b"payload"
    assert not temp_path.exists()
    assert_inside(final_path, backend.upload_root)

    await storage.delete(saved_key)
    assert not final_path.exists()


def test_local_storage_generated_names_do_not_collide(tmp_path) -> None:
    storage = DocumentStorageService(LocalStorageBackend(tmp_path / "uploads"))
    document_id = uuid4()

    keys = {storage.make_storage_key(document_id=document_id, extension=".pdf") for _ in range(20)}

    assert len(keys) == 20


def test_local_storage_rejects_path_traversal(tmp_path) -> None:
    backend = LocalStorageBackend(tmp_path / "uploads")

    with pytest.raises(StorageOperationError):
        backend.resolve_key("../outside.pdf")
    with pytest.raises(StorageOperationError):
        backend.resolve_key("/absolute.pdf")


@pytest.mark.anyio
async def test_local_storage_save_failure_keeps_temp_cleanup_under_caller_control(tmp_path) -> None:
    backend = LocalStorageBackend(tmp_path / "uploads")
    missing_temp = backend.temp_root / "missing.tmp"

    with pytest.raises(StorageOperationError):
        await backend.save(missing_temp, "safe/key.pdf")
