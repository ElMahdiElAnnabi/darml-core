from pathlib import Path
from typing import BinaryIO

from darml.application.ports.file_storage import FileStoragePort


class FileSystemStorage(FileStoragePort):
    def __init__(self, data_dir: Path):
        self._data_dir = Path(data_dir)
        self._data_dir.mkdir(parents=True, exist_ok=True)

    async def save_upload(self, build_id: str, filename: str, source: BinaryIO) -> Path:
        dst_dir = self.workspace(build_id)
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst = dst_dir / filename
        with dst.open("wb") as f:
            while True:
                chunk = source.read(1 << 20)  # 1 MiB
                if not chunk:
                    break
                f.write(chunk)
        return dst

    def workspace(self, build_id: str) -> Path:
        return self._data_dir / "builds" / build_id

    def artifact_path(self, build_id: str, filename: str) -> Path:
        return self.workspace(build_id) / filename
