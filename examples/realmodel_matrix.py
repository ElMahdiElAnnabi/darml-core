"""Run parse + check_size for every (real model × target) combination.

Pure Python — no compilation. Validates that:
  - all 5 fixtures parse cleanly
  - size_check correctly accepts/rejects per target
  - oversized models on MCUs are rejected (the right behavior)
"""

from __future__ import annotations

from pathlib import Path

from darml.container import get_container

FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures"
MODELS = [
    "micro_speech_proxy.tflite",
    "mnist_cnn.tflite",
    "mobilenet_v2.tflite",
    "random_forest_iris.pkl",
    "mlp.onnx",
]


def main() -> int:
    container = get_container()
    targets = container.list_targets.execute()

    # Header
    print(f"{'model':28s}  {'target':14s}  {'fits':4s}  "
          f"{'flash':>9s}  {'ram':>9s}  warning")
    print("-" * 100)

    for fname in MODELS:
        path = FIXTURES / fname
        if not path.exists():
            print(f"{fname}  MISSING — run tests/fixtures/make_real_models.py")
            continue
        try:
            info = container.parse_model.execute(path)
        except Exception as e:
            print(f"{fname}  parse FAILED: {e}")
            continue

        for target in targets:
            try:
                check = container.check_size.execute(info, target.id)
            except Exception as e:
                print(f"{fname:28s}  {target.id:14s}  ERR  parse: {e}")
                continue
            ok = "✓" if check.fits else "✗"
            flash = f"{check.model_flash_kb:.0f}/{check.target_flash_kb:.0f}"
            ram = f"{check.model_ram_kb:.0f}/{check.target_ram_kb:.0f}"
            warn = (check.warning or "").replace("\n", " ")[:50]
            print(f"{fname:28s}  {target.id:14s}  {ok:4s}  "
                  f"{flash:>9s}  {ram:>9s}  {warn}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
