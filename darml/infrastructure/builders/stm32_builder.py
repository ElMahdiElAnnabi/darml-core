from pathlib import Path

from darml.infrastructure.platformio.platformio_runner import PlatformIORunner

from .platformio_builder import PlatformIOBuilder, PlatformIOBuilderConfig


class STM32F4Builder(PlatformIOBuilder):
    def __init__(self, templates_root: Path, pio: PlatformIORunner):
        super().__init__(
            config=PlatformIOBuilderConfig(
                target_id="stm32f4",
                template_subdir="stm32",
                pio_environment="stm32f4",
                tensor_arena_min_bytes=32768,
                # STM32F4 (Nucleo F446RE) has 128 KB SRAM. After framework
                # + tflm_cortexm statics, ~96 KB is available for arena.
                tensor_arena_max_bytes=96 * 1024,
            ),
            templates_root=templates_root,
            pio=pio,
        )


class STM32H7Builder(PlatformIOBuilder):
    def __init__(self, templates_root: Path, pio: PlatformIORunner):
        super().__init__(
            config=PlatformIOBuilderConfig(
                target_id="stm32h7",
                template_subdir="stm32",
                pio_environment="stm32h7",
                tensor_arena_min_bytes=131072,
                # STM32H7 (Nucleo H743ZI) has 1 MB SRAM. Reserve ~256 KB
                # for framework + interpreter + buffers; rest goes to arena.
                tensor_arena_max_bytes=768 * 1024,
            ),
            templates_root=templates_root,
            pio=pio,
        )


class STM32N6Builder(PlatformIOBuilder):
    def __init__(self, templates_root: Path, pio: PlatformIORunner):
        super().__init__(
            config=PlatformIOBuilderConfig(
                target_id="stm32n6",
                template_subdir="stm32",
                pio_environment="stm32n6",
                tensor_arena_min_bytes=262144,
                # STM32N6 has 1.5 MB SRAM (preliminary spec).
                tensor_arena_max_bytes=1024 * 1024,
            ),
            templates_root=templates_root,
            pio=pio,
        )
