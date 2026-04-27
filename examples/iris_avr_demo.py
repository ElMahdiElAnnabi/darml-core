"""End-to-end Darml demo: sklearn iris classifier → AVR C library.

Trains a tiny scikit-learn DecisionTreeClassifier on the iris dataset,
saves it as a .pkl, then drives the Darml pipeline end-to-end:

    parse → check → quantize → convert → compile → package

For target `avr-mega328` with `output_kind=LIBRARY`, the pipeline:
  - parses the .pkl (SklearnParser)
  - estimates footprint vs the AVR's 2KB RAM / 32KB Flash
  - skips quantization (no quantizer registered for sklearn)
  - skips ONNX-to-TFLite conversion (target runtime is emlearn)
  - runs AVRBuilder → emlearn generates a model.h C header
  - packages the rendered project sources into a .zip

No cross-compiler is needed — `output_kind=LIBRARY` produces source code
the user can drop into their own AVR project.
"""

from __future__ import annotations

import asyncio
import sys
import zipfile
from pathlib import Path

import joblib
from sklearn.datasets import load_iris
from sklearn.tree import DecisionTreeClassifier

from darml.container import get_container
from darml.domain.enums import OutputKind, ReportMode
from darml.domain.models import BuildRequest


def train(out_path: Path) -> None:
    iris = load_iris()
    clf = DecisionTreeClassifier(max_depth=3, random_state=0)
    clf.fit(iris.data, iris.target)
    joblib.dump(clf, out_path)
    acc = clf.score(iris.data, iris.target)
    print(f"  trained DecisionTreeClassifier (max_depth=3): {acc:.0%} train accuracy")
    print(f"  saved to {out_path} ({out_path.stat().st_size} bytes)")


async def run() -> int:
    workspace = Path("./demo_workspace").resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    model_path = workspace / "iris.pkl"

    print("step 1 — train sklearn model")
    train(model_path)

    container = get_container()

    print("\nstep 2 — parse model (CLI: darml info iris.pkl)")
    info = container.parse_model.execute(model_path)
    print(f"  format={info.format.value}  input={list(info.input_shape)}  "
          f"output={list(info.output_shape)}  ops={list(info.ops_list)}")

    print("\nstep 3 — check fit on avr-mega328 (CLI: darml check iris.pkl --target avr-mega328)")
    check = container.check_size.execute(info, "avr-mega328")
    verdict = "FITS" if check.fits else "TOO LARGE"
    print(f"  [{verdict}] Flash {check.model_flash_kb:.2f} / {check.target_flash_kb:.0f} KB    "
          f"RAM {check.model_ram_kb:.2f} / {check.target_ram_kb:.0f} KB")
    if check.warning:
        print(f"  warning: {check.warning}")

    print("\nstep 4 — build library for avr-mega328 (CLI: darml build iris.pkl --target avr-mega328 --output library)")
    request = BuildRequest(
        model_path=model_path,
        target_id="avr-mega328",
        output_kind=OutputKind.LIBRARY,
        report_mode=ReportMode.SERIAL,
    )
    result = await container.build_firmware.execute(request)
    print(f"  status={result.status.value}  build_id={result.build_id}")
    if result.error:
        print(f"  ERROR: {result.error}", file=sys.stderr)
        for w in result.warnings:
            print(f"  warn:  {w}", file=sys.stderr)
        return 1
    for w in result.warnings:
        print(f"  warn:  {w}")

    print("\nstep 5 — inspect the artifact zip")
    print(f"  artifact: {result.artifact_zip_path}")
    if result.artifact_zip_path and result.artifact_zip_path.exists():
        with zipfile.ZipFile(result.artifact_zip_path) as zf:
            for name in zf.namelist():
                size = zf.getinfo(name).file_size
                print(f"    {name:35s} {size:>7} bytes")

    print(f"\n  library zip: {result.library_path}")
    if result.library_path and result.library_path.exists():
        with zipfile.ZipFile(result.library_path) as zf:
            for name in zf.namelist():
                size = zf.getinfo(name).file_size
                print(f"    {name:35s} {size:>7} bytes")

    print("\ndone.  Drop the contents of <target>-library.zip into your AVR project,")
    print("      compile with the existing platformio.ini, and flash with `darml flash`.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
