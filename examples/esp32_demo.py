"""End-to-end Darml demo: TFLite model → ESP32-S3 firmware build.

Drives the full pipeline (parse → check → quantize → convert → compile →
package) for `esp32-s3` with `output=firmware`.  Requires:
  - PlatformIO + the espressif32 platform (the runner fetches the cross-
    compiler toolchain on first run).
  - The ESP32 TFLite Micro library to resolve from `lib_deps` in the
    template's platformio.ini.

Run from the repo root:
    DARML_BUILD_TIMEOUT=1800 python examples/esp32_demo.py

Use a much higher timeout than the default 300s — first-time toolchain
downloads can take 10+ minutes.
"""

from __future__ import annotations

import asyncio
import sys
import zipfile
from pathlib import Path

from darml.container import get_container
from darml.domain.enums import OutputKind, ReportMode
from darml.domain.models import BuildRequest

FIXTURE = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "tiny_model.tflite"


async def run() -> int:
    if not FIXTURE.exists():
        print(f"Missing fixture: {FIXTURE}", file=sys.stderr)
        print("Generate it first: python tests/fixtures/make_tflite.py", file=sys.stderr)
        return 1

    container = get_container()

    print(f"step 1 — parse fixture {FIXTURE.name}")
    info = container.parse_model.execute(FIXTURE)
    print(f"  format={info.format.value}  input={list(info.input_shape)}  "
          f"output={list(info.output_shape)}  ops={info.num_ops}")

    print("\nstep 2 — check fit on esp32-s3")
    check = container.check_size.execute(info, "esp32-s3")
    print(f"  [{('FITS' if check.fits else 'TOO LARGE')}] "
          f"Flash {check.model_flash_kb:.2f} / {check.target_flash_kb:.0f} KB    "
          f"RAM {check.model_ram_kb:.2f} / {check.target_ram_kb:.0f} KB")

    print("\nstep 3 — build firmware (PlatformIO will fetch toolchain on first run)")
    request = BuildRequest(
        model_path=FIXTURE,
        target_id="esp32-s3",
        quantize=False,
        output_kind=OutputKind.FIRMWARE,
        report_mode=ReportMode.SERIAL,
    )
    result = await container.build_firmware.execute(request)
    print(f"  status={result.status.value}  build_id={result.build_id}")

    if result.error:
        print(f"\nERROR: {result.error}", file=sys.stderr)
        log_tail = "\n".join(result.build_log.splitlines()[-40:]) if result.build_log else ""
        if log_tail:
            print("---- last 40 lines of build log ----", file=sys.stderr)
            print(log_tail, file=sys.stderr)
        return 1

    print("\nstep 4 — inspect artifact")
    print(f"  artifact: {result.artifact_zip_path}")
    if result.artifact_zip_path and result.artifact_zip_path.exists():
        with zipfile.ZipFile(result.artifact_zip_path) as zf:
            for name in zf.namelist():
                print(f"    {name:35s} {zf.getinfo(name).file_size:>9} bytes")

    if result.firmware_path:
        print(f"\n  firmware: {result.firmware_path}")
        if result.firmware_path.exists():
            print(f"  size:     {result.firmware_path.stat().st_size} bytes")

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
