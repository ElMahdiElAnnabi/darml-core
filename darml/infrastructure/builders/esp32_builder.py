from pathlib import Path

from darml.infrastructure.platformio.platformio_runner import PlatformIORunner

from .platformio_builder import PlatformIOBuilder, PlatformIOBuilderConfig


class ESP32Builder(PlatformIOBuilder):
    """Original ESP32 (Xtensa LX6 — ESP-WROOM-32 / DevKit-V1 / NodeMCU-32S).

    520 KB total SRAM, ~320 KB usable as DRAM after IRAM split, no PSRAM on
    the default `esp32dev` board. Same arena budget as the S3 N8 variant.
    Switch to a WROVER board if you need PSRAM-backed arena.
    """

    def __init__(self, templates_root: Path, pio: PlatformIORunner):
        super().__init__(
            config=PlatformIOBuilderConfig(
                target_id="esp32",
                template_subdir="esp32",
                pio_environment="esp32",
                tensor_arena_min_bytes=65536,
                tensor_arena_max_bytes=150 * 1024,
            ),
            templates_root=templates_root,
            pio=pio,
        )


class ESP32S3Builder(PlatformIOBuilder):
    """ESP32-S3 (Xtensa LX7 — DevKitC-1 N8 / N16R8).

    512 KB internal SRAM + optional 8 MB PSRAM on R8 variants. The default
    arena cap is set for the N8 (no PSRAM); models that need more should
    switch to a PSRAM board.
    """

    def __init__(self, templates_root: Path, pio: PlatformIORunner):
        super().__init__(
            config=PlatformIOBuilderConfig(
                target_id="esp32-s3",
                template_subdir="esp32",
                pio_environment="esp32-s3",
                tensor_arena_min_bytes=65536,
                tensor_arena_max_bytes=150 * 1024,
            ),
            templates_root=templates_root,
            pio=pio,
        )
