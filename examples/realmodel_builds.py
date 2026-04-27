"""Drive real builds for the (model, target) pairs that fit, log a summary."""

from __future__ import annotations

import asyncio
import sys
import time
import traceback
from pathlib import Path

from darml.container import get_container
from darml.domain.enums import OutputKind, ReportMode
from darml.domain.models import BuildRequest

FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures"

# (model, target, output_kind) — the matrix we want to verify end-to-end.
JOBS: list[tuple[str, str, OutputKind]] = [
    ("random_forest_iris.pkl",     "avr-mega328", OutputKind.LIBRARY),
    ("mobilenet_v2.tflite",        "rpi5",        OutputKind.FIRMWARE),
    ("micro_speech_proxy.tflite",  "rpi5",        OutputKind.FIRMWARE),
    ("mnist_cnn.tflite",           "rpi5",        OutputKind.FIRMWARE),
    ("mlp.onnx",                   "rpi5",        OutputKind.FIRMWARE),
    ("micro_speech_proxy.tflite",  "esp32-s3",    OutputKind.FIRMWARE),
    ("mnist_cnn.tflite",           "stm32f4",     OutputKind.FIRMWARE),
    ("mlp.onnx",                   "esp32-s3",    OutputKind.FIRMWARE),
]


async def run_one(model: str, target: str, output_kind: OutputKind) -> dict:
    container = get_container()
    path = FIXTURES / model
    if not path.exists():
        return {"status": "MISSING", "model": model, "target": target}

    request = BuildRequest(
        model_path=path,
        target_id=target,
        quantize=False,
        output_kind=output_kind,
        report_mode=ReportMode.SERIAL,
    )
    t0 = time.perf_counter()
    try:
        result = await container.build_firmware.execute(request)
    except Exception as e:
        return {
            "status": "EXC",
            "model": model,
            "target": target,
            "error": f"{type(e).__name__}: {e}",
            "duration": time.perf_counter() - t0,
        }
    return {
        "status": result.status.value,
        "model": model,
        "target": target,
        "build_id": result.build_id,
        "error": result.error,
        "warnings": list(result.warnings),
        "firmware": str(result.firmware_path) if result.firmware_path else None,
        "library": str(result.library_path) if result.library_path else None,
        "duration": time.perf_counter() - t0,
    }


async def main() -> int:
    results = []
    for model, target, kind in JOBS:
        print(f"\n=== {model} → {target} ({kind.value}) ===")
        try:
            r = await run_one(model, target, kind)
        except Exception:
            traceback.print_exc()
            r = {"status": "CRASH", "model": model, "target": target}
        results.append(r)
        print(f"  status={r.get('status')}  duration={r.get('duration', 0):.1f}s")
        if r.get("error"):
            print(f"  error: {r['error']}")
        for w in r.get("warnings", []) or []:
            print(f"  warn: {w}")

    # Summary
    print("\n" + "=" * 60)
    print(f"{'model':28s}  {'target':14s}  {'output':10s}  {'status':10s}  time")
    print("-" * 78)
    for r in results:
        print(f"{r['model']:28s}  {r['target']:14s}  "
              f"{'firmware' if 'firmware' in (r.get('firmware') or '') else 'library':10s}  "
              f"{r.get('status', '?'):10s}  {r.get('duration', 0):>5.1f}s")

    return 0 if all(r.get("status") == "completed" for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
