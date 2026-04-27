from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from darml.application.ports.flasher import FlasherPort
from darml.domain.exceptions import FlashFailed


@dataclass
class FlashDevice:
    flashers: list[FlasherPort]

    def __init__(self, flashers: Iterable[FlasherPort]):
        self.flashers = list(flashers)

    def execute(self, firmware_path: Path, port: str, target_id: str) -> str:
        for flasher in self.flashers:
            if flasher.supports(target_id):
                return flasher.flash(firmware_path, port, target_id)
        raise FlashFailed(f"No flasher registered for target: {target_id}")
