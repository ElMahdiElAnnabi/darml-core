from dataclasses import dataclass, field
from pathlib import Path

from darml.domain.models import BuildRequest, BuildResult, ModelInfo


@dataclass
class BuildContext:
    """Shared state passed through each pipeline step."""

    request: BuildRequest
    result: BuildResult
    workspace: Path
    current_model_path: Path
    model_info: ModelInfo | None = None
    artifacts: dict[str, Path] = field(default_factory=dict)
