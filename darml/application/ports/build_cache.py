"""Build-cache port — short-circuit identical rebuilds.

Cache key is derived from the model bytes hash plus every input that affects
output: target, quantize flag, output kind, report mode, intervals, etc.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from darml.domain.models import BuildRequest, BuildResult


class BuildCachePort(ABC):
    @abstractmethod
    def key_for(self, request: BuildRequest) -> str:
        """Compute a stable cache key from a BuildRequest.

        Reads the model file off disk so the key reflects content, not path.
        """

    @abstractmethod
    def get(self, key: str, into_workspace: Path, build_id: str) -> BuildResult | None:
        """Return a populated BuildResult on hit (with artifacts copied into
        `into_workspace`), or None on miss."""

    @abstractmethod
    def put(self, key: str, result: BuildResult) -> None:
        """Persist this build's artifacts under `key`."""
