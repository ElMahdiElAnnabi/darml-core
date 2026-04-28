from pathlib import Path

from darml.infrastructure.platformio.platformio_runner import PlatformIORunner

from .platformio_builder import PlatformIOBuilder, PlatformIOBuilderConfig


class NRF52840Builder(PlatformIOBuilder):
    def __init__(self, templates_root: Path, pio: PlatformIORunner):
        super().__init__(
            config=PlatformIOBuilderConfig(
                target_id="nrf52840",
                template_subdir="nrf52840",
                pio_environment="nrf52840",
                tensor_arena_min_bytes=32 * 1024,
                # nRF52840 has 256 KB SRAM. Without softdevice, ~200 KB is
                # available; with softdevice S140 (BLE), ~140 KB. Cap at
                # 128 KB to leave headroom for either case.
                tensor_arena_max_bytes=128 * 1024,
            ),
            templates_root=templates_root,
            pio=pio,
        )
