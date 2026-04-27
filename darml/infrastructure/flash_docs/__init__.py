"""Per-target flash instructions, rendered into each build artifact .zip."""

from __future__ import annotations

from darml.domain.enums import OutputKind

# A single source of truth so the FLASH.md inside the zip and the `darml flash`
# command stay in sync.
_BLOCKS: dict[str, dict[str, str]] = {
    # MCU targets — firmware mode produces firmware.bin / firmware.hex.
    "esp32": {
        "tool": "esptool.py",
        "install": "pip install esptool",
        "command": (
            "esptool.py --chip esp32 --port /dev/ttyUSB0 --baud 921600 "
            "write_flash 0x1000 firmware.bin"
        ),
        "notes": (
            "Note: original ESP32 flashes the app at offset 0x1000 (the boot "
            "loader sits at 0x0 — leave it alone unless you've also rebuilt "
            "it). Most generic boards (DevKit-V1, NodeMCU-32S) auto-enter "
            "bootloader thanks to the EN/IO0 transistor circuit; if not, "
            "hold BOOT, tap EN, release BOOT. Serial monitor: 115200 baud."
        ),
    },
    "esp32-s3": {
        "tool": "esptool.py",
        "install": "pip install esptool",
        "command": (
            "esptool.py --chip esp32s3 --port /dev/ttyUSB0 --baud 921600 "
            "write_flash 0x0 firmware.bin"
        ),
        "notes": (
            "If the device doesn't auto-reset into bootloader, hold BOOT, "
            "tap RESET, release BOOT. After flashing: open a serial monitor "
            "at 115200 baud (`pio device monitor` or `screen /dev/ttyUSB0 "
            "115200`)."
        ),
    },
    "stm32f4": {
        "tool": "STM32_Programmer_CLI",
        "install": "https://www.st.com/en/development-tools/stm32cubeprog.html",
        "command": (
            "STM32_Programmer_CLI -c port=SWD -w firmware.bin 0x08000000 -v -rst"
        ),
        "notes": (
            "Connect ST-Link to the board's SWD header. For Nucleo boards "
            "the on-board ST-Link is usually visible without extra wiring. "
            "Serial monitor: 115200 baud."
        ),
    },
    "stm32h7": {
        "tool": "STM32_Programmer_CLI",
        "install": "https://www.st.com/en/development-tools/stm32cubeprog.html",
        "command": (
            "STM32_Programmer_CLI -c port=SWD -w firmware.bin 0x08000000 -v -rst"
        ),
        "notes": "Same as STM32F4. Larger flash; 0x08000000 base unchanged.",
    },
    "stm32n6": {
        "tool": "STM32_Programmer_CLI",
        "install": "https://www.st.com/en/development-tools/stm32cubeprog.html",
        "command": (
            "STM32_Programmer_CLI -c port=SWD -w firmware.bin 0x08000000 -v -rst"
        ),
        "notes": "STM32N6 boot mode + signing flow may require additional flags.",
    },
    "avr-mega328": {
        "tool": "avrdude",
        "install": "apt install avrdude  # or: brew install avrdude",
        "command": (
            "avrdude -p m328p -c arduino -P /dev/ttyUSB0 -b 115200 "
            "-U flash:w:firmware.hex:i"
        ),
        "notes": (
            "Adjust -P to the actual serial port. Many USB-UART bridges "
            "(CH340) need the corresponding driver."
        ),
    },
    "avr-mega2560": {
        "tool": "avrdude",
        "install": "apt install avrdude  # or: brew install avrdude",
        "command": (
            "avrdude -p m2560 -c wiring -P /dev/ttyACM0 -b 115200 -D "
            "-U flash:w:firmware.hex:i"
        ),
        "notes": "Mega 2560 uses the wiring programmer at 115200 baud.",
    },
    # Linux-class targets — bundle is a tarball, not firmware.
    "rpi4": {
        "tool": "ssh + docker",
        "install": "Raspberry Pi OS 64-bit, Docker installed.",
        "command": (
            "scp <bundle>.tar.gz pi@raspberrypi.local:/tmp/\n"
            "ssh pi@raspberrypi.local\n"
            "tar xzf /tmp/<bundle>.tar.gz && cd rpi4\n"
            "docker build -t darml-app . && docker run -it --rm darml-app"
        ),
        "notes": "Or run inference.py directly: `pip install -r requirements.txt && python inference.py`.",
    },
    "rpi5": {
        "tool": "ssh + docker",
        "install": "Raspberry Pi OS 64-bit, Docker installed.",
        "command": (
            "scp <bundle>.tar.gz pi@raspberrypi.local:/tmp/\n"
            "ssh pi@raspberrypi.local\n"
            "tar xzf /tmp/<bundle>.tar.gz && cd rpi5\n"
            "docker build -t darml-app . && docker run -it --rm darml-app"
        ),
        "notes": "Same as Pi 4; the binary is the same.",
    },
    "jetson-nano": {
        "tool": "ssh + docker (NVIDIA L4T)",
        "install": "JetPack 4.6+ with Docker.",
        "command": (
            "scp <bundle>.tar.gz user@jetson.local:/tmp/\n"
            "ssh user@jetson.local\n"
            "tar xzf /tmp/<bundle>.tar.gz && cd jetson-nano\n"
            "sudo docker build -t darml-app . && sudo docker run --runtime nvidia "
            "-it --rm darml-app"
        ),
        "notes": "GPU access requires --runtime nvidia (auto when nvidia-container-runtime is the default).",
    },
    "jetson-orin": {
        "tool": "ssh + docker (NVIDIA L4T)",
        "install": "JetPack 5.x+ with Docker.",
        "command": (
            "scp <bundle>.tar.gz user@jetson.local:/tmp/\n"
            "ssh user@jetson.local\n"
            "tar xzf /tmp/<bundle>.tar.gz && cd jetson-orin\n"
            "sudo docker build -t darml-app . && sudo docker run --runtime nvidia "
            "-it --rm darml-app"
        ),
        "notes": "Same flow as Nano; bigger model headroom thanks to 8 GB RAM.",
    },
}


def render_flash_readme(target_id: str, output_kind: OutputKind, build_id: str) -> str:
    block = _BLOCKS.get(target_id)
    if block is None:
        return f"Unknown target {target_id}; no flash instructions available.\n"

    if output_kind == OutputKind.LIBRARY:
        return (
            f"# Darml build {build_id} — {target_id} (library mode)\n\n"
            "This .zip contains the rendered project sources, not a flashable\n"
            "firmware. Drop the inner files into a PlatformIO (or equivalent)\n"
            "project and build with your preferred toolchain.\n"
        )

    return (
        f"# Darml build {build_id} — {target_id}\n\n"
        f"## Tool: {block['tool']}\n\n"
        f"### Install\n```\n{block['install']}\n```\n\n"
        f"### Flash command\n```\n{block['command']}\n```\n\n"
        f"### Notes\n{block['notes']}\n\n"
        "Or use the Darml CLI which auto-detects this target from the\n"
        "manifest.json bundled in this .zip:\n\n"
        f"```\ndarml flash <this.zip> --port /dev/ttyUSB0\n```\n"
    )


def flasher_id_for(target_id: str) -> str:
    """Map target_id to the abstract flasher key — used by `darml flash`."""
    if target_id.startswith("esp32"):
        return "esptool"
    if target_id.startswith("stm32"):
        return "stm32cube"
    if target_id.startswith("avr-"):
        return "avrdude"
    if target_id.startswith(("rpi", "jetson")):
        return "linux-bundle"
    return "unknown"
