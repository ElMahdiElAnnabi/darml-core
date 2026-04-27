from abc import ABC, abstractmethod
from pathlib import Path


class FlasherPort(ABC):
    """Flash a firmware artifact onto a physical device."""

    @abstractmethod
    def supports(self, target_id: str) -> bool: ...

    @abstractmethod
    def flash(self, firmware_path: Path, port: str, target_id: str) -> str: ...
