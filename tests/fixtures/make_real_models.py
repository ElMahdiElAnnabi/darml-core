"""Generate 5 real-world-shaped model fixtures locally.

These are not the exact public release weights, but the shapes/op coverage
match the canonical workloads we want to exercise:

  1. micro_speech_proxy.tflite — 1D-conv + dense keyword-spotter
     (matches the TFLite Micro examples/micro_speech architecture)
  2. mnist_cnn.tflite — small Conv2D + Dense classifier (~50 KB)
  3. mobilenet_v2.tflite — MobileNetV2 alpha=0.35, 96x96, INT8
     (representative of "image classifier on edge" — MCU rejection expected)
  4. random_forest_iris.pkl — scikit-learn DecisionTreeClassifier on iris
  5. mlp.onnx — multi-layer perceptron (ONNX path coverage)

Run from repo root:
    python tests/fixtures/make_real_models.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parent


def make_micro_speech_proxy() -> Path:
    import tensorflow as tf
    rng = np.random.default_rng(0)
    # 49 frames × 40 mfcc — same as TFLM micro_speech.
    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(49, 40, 1)),
        tf.keras.layers.Conv2D(8, (10, 4), strides=(2, 2), activation="relu", padding="same"),
        tf.keras.layers.MaxPool2D((2, 2)),
        tf.keras.layers.Flatten(),
        tf.keras.layers.Dense(16, activation="relu"),
        tf.keras.layers.Dense(4, activation="softmax"),  # 4 keywords
    ])
    model.compile(optimizer="adam", loss="sparse_categorical_crossentropy")
    model.fit(
        rng.random((32, 49, 40, 1)).astype(np.float32),
        rng.integers(0, 4, size=32),
        epochs=1, verbose=0,
    )
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    out = OUT / "micro_speech_proxy.tflite"
    out.write_bytes(converter.convert())
    return out


def make_mnist_cnn() -> Path:
    import tensorflow as tf
    rng = np.random.default_rng(0)
    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(28, 28, 1)),
        tf.keras.layers.Conv2D(8, 3, activation="relu", padding="same"),
        tf.keras.layers.MaxPool2D(),
        tf.keras.layers.Conv2D(16, 3, activation="relu", padding="same"),
        tf.keras.layers.MaxPool2D(),
        tf.keras.layers.Flatten(),
        tf.keras.layers.Dense(32, activation="relu"),
        tf.keras.layers.Dense(10, activation="softmax"),
    ])
    model.compile(optimizer="adam", loss="sparse_categorical_crossentropy")
    model.fit(
        rng.random((128, 28, 28, 1)).astype(np.float32),
        rng.integers(0, 10, size=128),
        epochs=1, verbose=0,
    )
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    out = OUT / "mnist_cnn.tflite"
    out.write_bytes(converter.convert())
    return out


def make_mobilenet_v2_int8() -> Path:
    import tensorflow as tf
    rng = np.random.default_rng(0)
    base = tf.keras.applications.MobileNetV2(
        input_shape=(96, 96, 3), alpha=0.35, include_top=False, weights=None,
    )
    model = tf.keras.Sequential([
        base,
        tf.keras.layers.GlobalAveragePooling2D(),
        tf.keras.layers.Dense(10, activation="softmax"),
    ])

    def representative():
        for _ in range(20):
            yield [rng.random((1, 96, 96, 3)).astype(np.float32)]

    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    converter.representative_dataset = representative
    converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
    converter.inference_input_type = tf.int8
    converter.inference_output_type = tf.int8
    out = OUT / "mobilenet_v2.tflite"
    out.write_bytes(converter.convert())
    return out


def make_random_forest() -> Path:
    import joblib
    from sklearn.datasets import load_iris
    from sklearn.ensemble import RandomForestClassifier

    iris = load_iris()
    clf = RandomForestClassifier(n_estimators=10, max_depth=4, random_state=0)
    clf.fit(iris.data, iris.target)
    out = OUT / "random_forest_iris.pkl"
    joblib.dump(clf, out)
    return out


def make_mlp_onnx() -> Path:
    import onnx
    from onnx import TensorProto, helper, numpy_helper
    rng = np.random.default_rng(0)
    w1 = rng.standard_normal((20, 64)).astype(np.float32)
    b1 = np.zeros((64,), dtype=np.float32)
    w2 = rng.standard_normal((64, 32)).astype(np.float32)
    b2 = np.zeros((32,), dtype=np.float32)
    w3 = rng.standard_normal((32, 5)).astype(np.float32)
    b3 = np.zeros((5,), dtype=np.float32)

    nodes = [
        helper.make_node("Gemm", ["x", "w1", "b1"], ["z1"]),
        helper.make_node("Relu", ["z1"], ["a1"]),
        helper.make_node("Gemm", ["a1", "w2", "b2"], ["z2"]),
        helper.make_node("Relu", ["z2"], ["a2"]),
        helper.make_node("Gemm", ["a2", "w3", "b3"], ["z3"]),
        helper.make_node("Softmax", ["z3"], ["y"], axis=1),
    ]
    graph = helper.make_graph(
        nodes,
        "mlp",
        inputs=[helper.make_tensor_value_info("x", TensorProto.FLOAT, [1, 20])],
        outputs=[helper.make_tensor_value_info("y", TensorProto.FLOAT, [1, 5])],
        initializer=[numpy_helper.from_array(t, n) for t, n in
                     [(w1, "w1"), (b1, "b1"), (w2, "w2"), (b2, "b2"), (w3, "w3"), (b3, "b3")]],
    )
    model = helper.make_model(
        graph,
        opset_imports=[helper.make_opsetid("", 13)],
        ir_version=9,
        producer_name="darml-fixture",
    )
    out = OUT / "mlp.onnx"
    onnx.save(model, str(out))
    return out


def main() -> int:
    builders = [
        ("micro_speech_proxy", make_micro_speech_proxy),
        ("mnist_cnn", make_mnist_cnn),
        ("mobilenet_v2", make_mobilenet_v2_int8),
        ("random_forest", make_random_forest),
        ("mlp_onnx", make_mlp_onnx),
    ]
    print("Generating real-world model fixtures …")
    for name, fn in builders:
        try:
            path = fn()
            kb = path.stat().st_size / 1024
            print(f"  ✓ {name:22s} → {path.name:30s} {kb:>9.1f} KB")
        except Exception as e:
            print(f"  ✗ {name:22s} failed: {e}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
