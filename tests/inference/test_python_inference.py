"""Tier A — Python-side inference smoke tests.

Each bundled fixture loads through its native runtime and runs inference
on dummy input. Output shape/dtype must match what each runtime reports;
no NaN or Inf in the result.

These are 'does the model file actually work' tests — they catch broken
fixtures, broken parsers, and (transitively) any ONNX/TFLite version
incompatibilities introduced by dependency upgrades.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

FIX = Path(__file__).resolve().parent.parent / "fixtures"


@pytest.mark.parametrize("fname", [
    "tiny_model.tflite",
    "micro_speech_proxy.tflite",
    "mnist_cnn.tflite",
    "mobilenet_v2.tflite",
])
def test_tflite_inference(fname):
    """Each TFLite fixture loads + runs on dummy input."""
    tf = pytest.importorskip("tensorflow")
    path = FIX / fname
    if not path.exists():
        pytest.skip(f"fixture missing: {fname} (run tests/fixtures/make_real_models.py)")

    interp = tf.lite.Interpreter(model_path=str(path))
    interp.allocate_tensors()
    inp = interp.get_input_details()[0]
    out = interp.get_output_details()[0]

    rng = np.random.default_rng(42)
    if inp["dtype"] == np.int8:
        data = rng.integers(-128, 127, size=inp["shape"], dtype=np.int8, endpoint=True)
    elif inp["dtype"] == np.uint8:
        data = rng.integers(0, 255, size=inp["shape"], dtype=np.uint8, endpoint=True)
    else:
        data = rng.standard_normal(inp["shape"]).astype(inp["dtype"])

    interp.set_tensor(inp["index"], data)
    interp.invoke()
    result = interp.get_tensor(out["index"])

    assert tuple(result.shape) == tuple(out["shape"]), (
        f"{fname}: output shape {result.shape} != declared {tuple(out['shape'])}"
    )
    assert result.dtype == out["dtype"], (
        f"{fname}: output dtype {result.dtype} != declared {out['dtype']}"
    )
    if np.issubdtype(result.dtype, np.floating):
        assert np.all(np.isfinite(result)), f"{fname}: NaN or Inf in output"


def test_onnx_inference():
    """The ONNX MLP fixture runs end-to-end via onnxruntime."""
    ort = pytest.importorskip("onnxruntime")
    path = FIX / "mlp.onnx"
    if not path.exists():
        pytest.skip("fixture missing: mlp.onnx")

    sess = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
    inp_meta = sess.get_inputs()[0]
    out_meta = sess.get_outputs()[0]

    rng = np.random.default_rng(42)
    shape = [d if isinstance(d, int) and d > 0 else 1 for d in inp_meta.shape]
    data = rng.standard_normal(shape).astype(np.float32)

    out = sess.run(None, {inp_meta.name: data})[0]
    expected_last = [d for d in out_meta.shape if isinstance(d, int) and d > 0][-1]
    assert out.shape[-1] == expected_last, (
        f"mlp.onnx: output last dim {out.shape[-1]} != declared {expected_last}"
    )
    assert np.all(np.isfinite(out)), "mlp.onnx: NaN or Inf in output"

    # Softmax is applied in the model — outputs should sum to ~1 per sample.
    assert abs(out.sum() - out.shape[0]) < 1e-3, (
        f"mlp.onnx softmax row-sum off: {out.sum()}"
    )


def test_sklearn_inference():
    """The random-forest iris fixture predicts on dummy 4-feature input."""
    joblib = pytest.importorskip("joblib")
    path = FIX / "random_forest_iris.pkl"
    if not path.exists():
        pytest.skip("fixture missing: random_forest_iris.pkl")

    model = joblib.load(path)
    rng = np.random.default_rng(42)
    data = rng.standard_normal((3, 4)).astype(np.float32)

    pred = model.predict(data)
    assert pred.shape == (3,)
    assert all(p in {0, 1, 2} for p in pred), f"unexpected classes: {pred}"

    proba = model.predict_proba(data)
    assert proba.shape == (3, 3)
    # Each row of probabilities sums to ~1
    row_sums = proba.sum(axis=1)
    assert np.allclose(row_sums, 1.0, atol=1e-6), f"proba rows don't sum to 1: {row_sums}"
