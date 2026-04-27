import subprocess
from pathlib import Path

from darml.application.ports.flasher import FlasherPort
from darml.domain.exceptions import FlashFailed


class EsptoolFlasher(FlasherPort):
    """Flash ESP32 firmware via esptool.py."""

    def supports(self, target_id: str) -> bool:
        return target_id.startswith("esp32")

    def flash(self, firmware_path: Path, port: str, target_id: str) -> str:
        chip = "esp32s3" if target_id == "esp32-s3" else "esp32"
        # ESP32-S3 (Arduino-PIO) ships a merged image with bootloader at 0x0.
        # Original ESP32: bootloader is at 0x1000 in the partition table; the
        # application written by PIO is the merged image starting at 0x1000.
        offset = "0x0" if target_id == "esp32-s3" else "0x1000"
        cmd = [
            "esptool.py", "--chip", chip, "--port", port,
            "write_flash", offset, str(firmware_path),
        ]
        return _run(cmd)


class AvrdudeFlasher(FlasherPort):
    """Flash AVR firmware via avrdude."""

    def supports(self, target_id: str) -> bool:
        return target_id.startswith("avr-")

    def flash(self, firmware_path: Path, port: str, target_id: str) -> str:
        mcu_map = {"avr-mega328": "m328p", "avr-mega2560": "m2560"}
        mcu = mcu_map.get(target_id, "m328p")
        cmd = [
            "avrdude", "-p", mcu, "-c", "arduino", "-P", port,
            "-U", f"flash:w:{firmware_path}:i",
        ]
        return _run(cmd)


class STM32Flasher(FlasherPort):
    """Flash STM32 firmware via STM32_Programmer_CLI."""

    def supports(self, target_id: str) -> bool:
        return target_id.startswith("stm32")

    def flash(self, firmware_path: Path, port: str, target_id: str) -> str:
        cmd = [
            "STM32_Programmer_CLI", "-c", f"port={port}",
            "-w", str(firmware_path), "0x08000000", "-v", "-rst",
        ]
        return _run(cmd)


def _run(cmd: list[str]) -> str:
    try:
        completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError as e:
        raise FlashFailed(f"Flash tool not found: {cmd[0]}") from e
    if completed.returncode != 0:
        raise FlashFailed(f"Flash failed:\n{completed.stdout}\n{completed.stderr}")
    return completed.stdout
