"""End-to-end Darml demo: ONNX classifier → quantized → TFLite → RPi tarball.

Builds a tiny ONNX model directly from `onnx.helper` (no PyTorch/tf2onnx
needed), runs the full Darml pipeline (parse → check → quantize → convert →
compile → package), and inspects the resulting tarball.

Targets `rpi5` so no cross-compiler toolchain is required — the build is
pure-Python tarball packaging.
"""

from __future__ import annotations

import asyncio
import sys
import tarfile
import zipfile
from pathlib import Path

import numpy as np
import onnx
from onnx import TensorProto, helper, numpy_helper

from darml.container import get_container
from darml.domain.enums import OutputKind, ReportMode
from darml.domain.models import BuildRequest


def make_tiny_onnx(out_path: Path) -> None:
    """Build a 10→16→3 dense classifier as ONNX (Gemm + Relu + Gemm + Softmax).

    Construction is hand-rolled via onnx.helper to avoid pulling in PyTorch
    or tf2onnx — both add hundreds of MB of deps just for this fixture.
    """
    rng = np.random.default_rng(0)
    w1 = rng.standard_normal((10, 16)).astype(np.float32)
    b1 = np.zeros((16,), dtype=np.float32)
    w2 = rng.standard_normal((16, 3)).astype(np.float32)
    b2 = np.zeros((3,), dtype=np.float32)

    nodes = [
        helper.make_node("Gemm", ["x", "w1", "b1"], ["z1"], alpha=1.0, beta=1.0),
        helper.make_node("Relu", ["z1"], ["a1"]),
        helper.make_node("Gemm", ["a1", "w2", "b2"], ["z2"], alpha=1.0, beta=1.0),
        helper.make_node("Softmax", ["z2"], ["y"], axis=1),
    ]
    graph = helper.make_graph(
        nodes,
        "tiny_classifier",
        inputs=[helper.make_tensor_value_info("x", TensorProto.FLOAT, [1, 10])],
        outputs=[helper.make_tensor_value_info("y", TensorProto.FLOAT, [1, 3])],
        initializer=[
            numpy_helper.from_array(w1, "w1"),
            numpy_helper.from_array(b1, "b1"),
            numpy_helper.from_array(w2, "w2"),
            numpy_helper.from_array(b2, "b2"),
        ],
    )
    model = helper.make_model(
        graph,
        opset_imports=[helper.make_opsetid("", 13)],
        ir_version=9,
        producer_name="darml-demo",
    )
    onnx.save(model, str(out_path))
    print(f"  built tiny ONNX classifier → {out_path} ({out_path.stat().st_size} bytes)")


async def run() -> int:
    workspace = Path("./demo_workspace").resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    onnx_path = workspace / "tiny.onnx"

    print("step 1 — build tiny ONNX classifier")
    make_tiny_onnx(onnx_path)

    container = get_container()

    print("\nstep 2 — parse ONNX (CLI: darml info tiny.onnx)")
    info = container.parse_model.execute(onnx_path)
    print(f"  format={info.format.value}  input={list(info.input_shape)}  "
          f"output={list(info.output_shape)}  ops={list(info.ops_list)}")

    print("\nstep 3 — check fit on rpi5")
    check = container.check_size.execute(info, "rpi5")
    print(f"  [{('FITS' if check.fits else 'TOO LARGE')}] "
          f"Flash {check.model_flash_kb:.2f} / {check.target_flash_kb:.0f} KB    "
          f"RAM {check.model_ram_kb:.2f} / {check.target_ram_kb:.0f} KB")

    print("\nstep 4 — build with quantize=true (ONNX→quantized ONNX→TFLite→tarball)")
    request = BuildRequest(
        model_path=onnx_path,
        target_id="rpi5",
        quantize=True,
        output_kind=OutputKind.FIRMWARE,
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

    print("\nstep 5 — inspect the build artifacts")
    print(f"  artifact: {result.artifact_zip_path}")
    if result.artifact_zip_path and result.artifact_zip_path.exists():
        with zipfile.ZipFile(result.artifact_zip_path) as zf:
            for name in zf.namelist():
                print(f"    {name:40s} {zf.getinfo(name).file_size:>8} bytes")

    print(f"\n  firmware (rpi5 tarball): {result.firmware_path}")
    if result.firmware_path and result.firmware_path.exists():
        with tarfile.open(result.firmware_path) as tar:
            for m in tar.getmembers():
                if m.isfile():
                    print(f"    {m.name:40s} {m.size:>8} bytes")

    if result.quantize_result:
        q = result.quantize_result
        print(
            f"\n  quantization: {q.original_size_bytes} → {q.quantized_size_bytes} bytes "
            f"({q.compression_ratio:.2f}x compression)"
        )

    print("\ndone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
