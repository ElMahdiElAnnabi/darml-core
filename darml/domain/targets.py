from .enums import Runtime
from .models import Target

TARGETS: dict[str, Target] = {
    "avr-mega328": Target(
        id="avr-mega328",
        ram_kb=2,
        flash_kb=32,
        runtime=Runtime.EMLEARN,
        platformio_board="ATmega328P",
        platformio_platform="atmelavr",
    ),
    "avr-mega2560": Target(
        id="avr-mega2560",
        ram_kb=8,
        flash_kb=256,
        runtime=Runtime.EMLEARN,
        platformio_board="megaatmega2560",
        platformio_platform="atmelavr",
    ),
    "stm32f4": Target(
        id="stm32f4",
        ram_kb=320,
        flash_kb=1024,
        runtime=Runtime.TFLITE_MICRO,
        platformio_board="nucleo_f446re",
        platformio_platform="ststm32",
    ),
    "stm32h7": Target(
        id="stm32h7",
        ram_kb=1024,
        flash_kb=2048,
        runtime=Runtime.TFLITE_MICRO,
        platformio_board="nucleo_h743zi",
        platformio_platform="ststm32",
    ),
    "stm32n6": Target(
        id="stm32n6",
        ram_kb=1536,
        flash_kb=4096,
        runtime=Runtime.TFLITE_MICRO,
        platformio_board="nucleo_n657x0",
        platformio_platform="ststm32",
    ),
    "esp32": Target(
        id="esp32",
        # Original ESP32 (Xtensa LX6, e.g. ESP-WROOM-32). 520 KB internal SRAM
        # is the chip total — usable DRAM segment is ~320 KB after IRAM split.
        # esp32dev is the most common PlatformIO board; covers DevKit-V1,
        # NodeMCU-32S, generic WROOM modules. WROVER variants have PSRAM —
        # change board + bump psram_kb if you target one.
        ram_kb=520,
        flash_kb=4096,
        runtime=Runtime.TFLITE_MICRO,
        psram_kb=0,
        platformio_board="esp32dev",
        platformio_platform="espressif32",
    ),
    "esp32-s3": Target(
        id="esp32-s3",
        ram_kb=512,
        flash_kb=16384,
        runtime=Runtime.TFLITE_MICRO,
        psram_kb=8192,
        platformio_board="esp32-s3-devkitc-1",
        platformio_platform="espressif32",
    ),
    "rpi4": Target(
        id="rpi4",
        ram_kb=4 * 1024 * 1024,
        flash_kb=0,
        runtime=Runtime.TFLITE,
    ),
    "rpi5": Target(
        id="rpi5",
        ram_kb=8 * 1024 * 1024,
        flash_kb=0,
        runtime=Runtime.TFLITE,
    ),
    "jetson-nano": Target(
        id="jetson-nano",
        ram_kb=4 * 1024 * 1024,
        flash_kb=0,
        runtime=Runtime.TENSORRT,
    ),
    "jetson-orin": Target(
        id="jetson-orin",
        ram_kb=8 * 1024 * 1024,
        flash_kb=0,
        runtime=Runtime.TENSORRT,
    ),
}


def get_target(target_id: str) -> Target | None:
    return TARGETS.get(target_id)


def list_targets() -> list[Target]:
    return list(TARGETS.values())
