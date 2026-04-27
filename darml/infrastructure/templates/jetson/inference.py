"""Darml Jetson inference runner — uses TFLite runtime by default.

Swap in TensorRT by loading a `.plan` engine if you've converted the model.
"""

import os
import sys
import time
from pathlib import Path

MODEL_PATH = Path(__file__).parent / "model.tflite"


def main() -> int:
    try:
        import tensorflow as tf  # type: ignore
        Interpreter = tf.lite.Interpreter
    except ImportError:
        print("error: install tensorflow on the Jetson image", file=sys.stderr)
        return 1

    interpreter = Interpreter(model_path=str(MODEL_PATH))
    interpreter.allocate_tensors()
    inp = interpreter.get_input_details()[0]
    out = interpreter.get_output_details()[0]

    interval = float(os.getenv("DARML_INTERVAL_S", "1.0"))
    while True:
        import numpy as np  # type: ignore
        data = np.zeros(inp["shape"], dtype=inp["dtype"])
        interpreter.set_tensor(inp["index"], data)
        t0 = time.perf_counter()
        interpreter.invoke()
        dt = (time.perf_counter() - t0) * 1e3
        result = interpreter.get_tensor(out["index"])
        print(
            f"[Darml] pred={int(result.argmax())} "
            f"conf={float(result.max()):.3f} latency={dt:.2f}ms",
            flush=True,
        )
        time.sleep(interval)


if __name__ == "__main__":
    raise SystemExit(main())
