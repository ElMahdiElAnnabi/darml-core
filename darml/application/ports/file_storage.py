from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO


class FileStoragePort(ABC):
    """Filesystem abstraction for uploads, workspaces, and artifacts."""

    @abstractmethod
    async def save_upload(self, build_id: str, filename: str, source: BinaryIO) -> Path: ...

    @abstractmethod
    def workspace(self, build_id: str) -> Path: ...

    @abstractmethod
    def artifact_path(self, build_id: str, filename: str) -> Path: ...
