from pathlib import Path
from typing import BinaryIO

from darml.application.ports.file_storage import FileStoragePort


class FileSystemStorage(FileStoragePort):
    def __init__(self, data_dir: Path):
        self._data_dir = Path(data_dir).resolve()
        self._data_dir.mkdir(parents=True, exist_ok=True)

    async def save_upload(self, build_id: str, filename: str, source: BinaryIO) -> Path:
        dst_dir = self.workspace(build_id)
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst = self._safe_join(dst_dir, filename)
        with dst.open("wb") as f:
            while True:
                chunk = source.read(1 << 20)  # 1 MiB
                if not chunk:
                    break
                f.write(chunk)
        return dst

    def workspace(self, build_id: str) -> Path:
        return self._safe_join(self._data_dir / "builds", build_id)

    def artifact_path(self, build_id: str, filename: str) -> Path:
        return self._safe_join(self.workspace(build_id), filename)

    def _safe_join(self, base: Path, child: str) -> Path:
        """Join `child` onto `base` and assert the result stays under base.

        Defense against path traversal. We assert relativity to BASE
        (not just data_dir), so `child='..'` — which would land on
        data_dir/ instead of data_dir/builds/ — also gets caught. Today
        build_id values are server-minted UUIDs, but if a future code
        path lets a user pick the build_id or filename, this stops an
        unfiltered '..' from escaping the intended directory.
        """
        base_resolved = base.resolve()
        joined = (base / child).resolve()
        try:
            joined.relative_to(base_resolved)
        except ValueError:
            raise ValueError(
                f"Refusing path traversal: {child!r} (resolved to {joined}) "
                f"is outside {base_resolved}."
            )
        # Belt-and-suspenders: must also stay under data_dir at the top level.
        try:
            joined.relative_to(self._data_dir)
        except ValueError:
            raise ValueError(
                f"Refusing path traversal: {child!r} (resolved to {joined}) "
                f"is outside data_dir {self._data_dir}."
            )
        return joined
