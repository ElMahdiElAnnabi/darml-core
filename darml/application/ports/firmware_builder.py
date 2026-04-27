from abc import ABC, abstractmethod
from pathlib import Path

from darml.domain.models import BuildRequest, BuildResult, ModelInfo


class FirmwareBuilderPort(ABC):
    """Compile a model + template into a flashable artifact for one target."""

    @property
    @abstractmethod
    def target_id(self) -> str: ...

    @abstractmethod
    async def build(
        self,
        request: BuildRequest,
        model_info: ModelInfo,
        model_path: Path,
        workspace: Path,
    ) -> BuildResult: ...
