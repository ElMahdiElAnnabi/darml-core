"""End-to-end Darml demo: TFLite model → STM32F4 firmware build."""

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
        return 1

    container = get_container()

    print(f"step 1 — parse {FIXTURE.name}")
    info = container.parse_model.execute(FIXTURE)
    print(f"  format={info.format.value}  input={list(info.input_shape)}  "
          f"output={list(info.output_shape)}  ops={info.num_ops}")

    print("\nstep 2 — check fit on stm32f4")
    check = container.check_size.execute(info, "stm32f4")
    print(f"  [{('FITS' if check.fits else 'TOO LARGE')}] "
          f"Flash {check.model_flash_kb:.2f} / {check.target_flash_kb:.0f} KB    "
          f"RAM {check.model_ram_kb:.2f} / {check.target_ram_kb:.0f} KB")

    print("\nstep 3 — build firmware (PlatformIO will fetch tflm_cortexm + ARM toolchain)")
    request = BuildRequest(
        model_path=FIXTURE,
        target_id="stm32f4",
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
