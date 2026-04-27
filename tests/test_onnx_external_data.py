"""ONNXParser must handle 'external data' models cleanly.

ONNX splits big models (>2 GB) into a `.onnx` graph file plus one or
more `.onnx.data` sidecar files. When users upload only the .onnx, our
parser must extract metadata WITHOUT trying to dereference the missing
weight file.
"""

from __future__ import annotations

import numpy as np
import onnx
from onnx import TensorProto, external_data_helper, helper, numpy_helper

from darml.domain.enums import ModelFormat
from darml.infrastructure.parsers.onnx_parser import ONNXParser


def _build_external_data_onnx(tmp_path):
    """Build a tiny ONNX model whose weights live in a sidecar .data file."""
    rng = np.random.default_rng(0)
    w = rng.standard_normal((4, 8)).astype(np.float32)
    b = np.zeros((8,), dtype=np.float32)

    nodes = [helper.make_node("Gemm", ["x", "w", "b"], ["y"], alpha=1.0, beta=1.0)]
    graph = helper.make_graph(
        nodes,
        "tiny_external",
        inputs=[helper.make_tensor_value_info("x", TensorProto.FLOAT, [1, 4])],
        outputs=[helper.make_tensor_value_info("y", TensorProto.FLOAT, [1, 8])],
        initializer=[
            numpy_helper.from_array(w, "w"),
            numpy_helper.from_array(b, "b"),
        ],
    )
    model = helper.make_model(
        graph,
        opset_imports=[helper.make_opsetid("", 13)],
        ir_version=9,
    )
    onnx_path = tmp_path / "tiny.onnx"
    # ONNX's external-data save only externalizes tensors above a default
    # size threshold (~1024 bytes). Our test weights are tiny, so we force
    # external storage for *every* tensor with size_threshold=0.
    onnx.save_model(
        model, str(onnx_path),
        save_as_external_data=True,
        all_tensors_to_one_file=True,
        location="tiny.onnx.data",
        size_threshold=0,
    )
    return onnx_path


def test_parse_external_data_onnx_when_sidecar_present(tmp_path):
    """The .data sidecar IS in the same dir → parses fine."""
    onnx_path = _build_external_data_onnx(tmp_path)
    info = ONNXParser().parse(onnx_path)
    assert info.format == ModelFormat.ONNX
    assert info.input_shape == (1, 4)
    assert info.output_shape == (1, 8)
    assert info.num_ops == 1


def test_parse_external_data_onnx_when_sidecar_missing(tmp_path):
    """User uploaded only the .onnx graph file — parser must still
    extract metadata via load_external_data=False (the bug we just fixed)."""
    onnx_path = _build_external_data_onnx(tmp_path)
    # Simulate "user only uploaded the graph file" by deleting the sidecar.
    sidecar = tmp_path / "tiny.onnx.data"
    assert sidecar.exists(), "test setup: sidecar should have been created"
    sidecar.unlink()

    # The fixed parser should still extract metadata.
    info = ONNXParser().parse(onnx_path)
    assert info.format == ModelFormat.ONNX
    assert info.input_shape == (1, 4)
    assert info.output_shape == (1, 8)
    assert info.num_ops == 1
