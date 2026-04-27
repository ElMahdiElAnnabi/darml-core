from abc import ABC, abstractmethod
from pathlib import Path

from darml.domain.enums import ModelFormat
from darml.domain.models import ModelInfo


class ModelParserPort(ABC):
    """Parse a model file and extract metadata."""

    @property
    @abstractmethod
    def format(self) -> ModelFormat: ...

    @abstractmethod
    def parse(self, path: Path) -> ModelInfo: ...
