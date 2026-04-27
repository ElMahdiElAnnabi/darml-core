import shutil
import tarfile
from pathlib import Path

from darml.application.ports.firmware_builder import FirmwareBuilderPort
from darml.domain.enums import BuildStatus
from darml.domain.exceptions import BuildFailed
from darml.domain.models import BuildRequest, BuildResult, ModelInfo
from darml.infrastructure.builders.rpi_builder import _IGNORE_NAMES, _strip_debris


class JetsonBuilder(FirmwareBuilderPort):
    """Jetson target — Docker-based bundle, similar to RPi."""

    def __init__(self, target_id: str, templates_root: Path):
        self._target_id = target_id
        self._template_dir = templates_root / "jetson"

    @property
    def target_id(self) -> str:
        return self._target_id

    async def build(
        self,
        request: BuildRequest,
        model_info: ModelInfo,
        model_path: Path,
        workspace: Path,
    ) -> BuildResult:
        result = BuildResult.new(target_id=self._target_id)
        try:
            bundle_dir = workspace / "bundle"
            if bundle_dir.exists():
                shutil.rmtree(bundle_dir)
            shutil.copytree(
                self._template_dir,
                bundle_dir,
                ignore=shutil.ignore_patterns(*_IGNORE_NAMES),
            )
            shutil.copy2(model_path, bundle_dir / f"model{model_path.suffix}")

            tarball = workspace / f"{self._target_id}.tar.gz"
            with tarfile.open(tarball, "w:gz") as tar:
                tar.add(bundle_dir, arcname=self._target_id, filter=_strip_debris)

            result.firmware_path = tarball
            result.status = BuildStatus.COMPLETED
            return result
        except Exception as e:
            raise BuildFailed(f"jetson build failed: {e}") from e


class JetsonNanoBuilder(JetsonBuilder):
    def __init__(self, templates_root: Path):
        super().__init__("jetson-nano", templates_root)


class JetsonOrinBuilder(JetsonBuilder):
    def __init__(self, templates_root: Path):
        super().__init__("jetson-orin", templates_root)
