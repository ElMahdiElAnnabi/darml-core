"""Darml Raspberry Pi inference runner.

Loads the bundled model.tflite via tflite-runtime and prints predictions.
Drop in your own sensor/camera capture where noted.
"""

import os
import sys
import time
from pathlib import Path

MODEL_PATH = Path(__file__).parent / "model.tflite"


def main() -> int:
    try:
        from tflite_runtime.interpreter import Interpreter  # type: ignore
    except ImportError:
        try:
            import tensorflow as tf  # type: ignore
            Interpreter = tf.lite.Interpreter  # noqa: N806
        except ImportError:
            print("error: install tflite-runtime or tensorflow", file=sys.stderr)
            return 1

    if not MODEL_PATH.exists():
        print(f"error: {MODEL_PATH} missing", file=sys.stderr)
        return 1

    interpreter = Interpreter(model_path=str(MODEL_PATH))
    interpreter.allocate_tensors()
    inp = interpreter.get_input_details()[0]
    out = interpreter.get_output_details()[0]

    interval = float(os.getenv("DARML_INTERVAL_S", "1.0"))
    while True:
        import numpy as np  # type: ignore
        data = np.zeros(inp["shape"], dtype=inp["dtype"])  # <<< capture sensor data here
        interpreter.set_tensor(inp["index"], data)
        t0 = time.perf_counter()
        interpreter.invoke()
        dt = (time.perf_counter() - t0) * 1e3
        result = interpreter.get_tensor(out["index"])
        pred = int(result.argmax())
        conf = float(result.max())
        print(f"[Darml] pred={pred} conf={conf:.3f} latency={dt:.2f}ms", flush=True)
        time.sleep(interval)


if __name__ == "__main__":
    raise SystemExit(main())
