"""Generate a tiny .tflite fixture (10→16→3 dense classifier)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import tensorflow as tf


def build_and_save(out_path: Path) -> None:
    keras_model = tf.keras.Sequential(
        [
            tf.keras.layers.Input(shape=(10,), name="features"),
            tf.keras.layers.Dense(16, activation="relu"),
            tf.keras.layers.Dense(3, activation="softmax", name="logits"),
        ]
    )
    keras_model.compile(optimizer="adam", loss="sparse_categorical_crossentropy")
    keras_model.fit(
        np.random.RandomState(0).randn(64, 10).astype(np.float32),
        np.random.RandomState(0).randint(0, 3, size=64),
        epochs=1, verbose=0,
    )

    converter = tf.lite.TFLiteConverter.from_keras_model(keras_model)
    out_path.write_bytes(converter.convert())
    print(f"  saved tiny TFLite → {out_path} ({out_path.stat().st_size} bytes)")


if __name__ == "__main__":
    out = Path(__file__).parent / "tiny_model.tflite"
    build_and_save(out)
