"""Path-traversal regression tests for FilesystemStorage."""

from __future__ import annotations

from pathlib import Path

import pytest

from darml.infrastructure.storage.filesystem_storage import FileSystemStorage


@pytest.fixture
def storage(tmp_path: Path) -> FileSystemStorage:
    return FileSystemStorage(tmp_path)


def test_workspace_for_clean_uuid_works(storage: FileSystemStorage) -> None:
    p = storage.workspace("11111111-2222-3333-4444-555555555555")
    assert "builds" in p.parts
    assert p.is_relative_to(storage._data_dir)


@pytest.mark.parametrize("evil", [
    "../../../etc/passwd",
    "../../../..",
    "..",
    "foo/../../etc/passwd",
    "/absolute/path/escape",
    "subdir/../../escape",
])
def test_workspace_rejects_traversal(
    storage: FileSystemStorage, evil: str,
) -> None:
    """Any build_id that resolves outside data_dir must crash, not silently
    write to /etc/ or /tmp/."""
    with pytest.raises(ValueError, match="traversal"):
        storage.workspace(evil)


def test_artifact_path_rejects_traversal(storage: FileSystemStorage) -> None:
    with pytest.raises(ValueError, match="traversal"):
        storage.artifact_path("good-id", "../../../etc/passwd")


def test_artifact_path_accepts_simple_filename(
    storage: FileSystemStorage,
) -> None:
    p = storage.artifact_path("good-id", "firmware.bin")
    assert p.name == "firmware.bin"
    assert p.is_relative_to(storage._data_dir)
