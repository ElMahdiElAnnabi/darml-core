from collections.abc import Iterable

from darml.application.ports.firmware_builder import FirmwareBuilderPort
from darml.domain.exceptions import TargetUnknown


class BuilderFactory:
    """Select the right FirmwareBuilder for a given target."""

    def __init__(self, builders: Iterable[FirmwareBuilderPort]):
        self._builders: dict[str, FirmwareBuilderPort] = {b.target_id: b for b in builders}

    def for_target(self, target_id: str) -> FirmwareBuilderPort:
        builder = self._builders.get(target_id)
        if builder is None:
            raise TargetUnknown(f"No builder registered for target: {target_id}")
        return builder

    def supported_targets(self) -> list[str]:
        return list(self._builders.keys())
