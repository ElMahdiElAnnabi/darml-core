from pathlib import Path

from darml.infrastructure.platformio.platformio_runner import PlatformIORunner

from .platformio_builder import PlatformIOBuilder, PlatformIOBuilderConfig


class RP2040Builder(PlatformIOBuilder):
    def __init__(self, templates_root: Path, pio: PlatformIORunner):
        super().__init__(
            config=PlatformIOBuilderConfig(
                target_id="rp2040",
                template_subdir="rp2040",
                pio_environment="rp2040",
                tensor_arena_min_bytes=32 * 1024,
                # RP2040 has 264 KB SRAM. The arduino-pico core reserves
                # ~32 KB for stacks + USB + framework; cap arena at 192 KB.
                tensor_arena_max_bytes=192 * 1024,
            ),
            templates_root=templates_root,
            pio=pio,
        )
