from enum import Enum


class ModelFormat(str, Enum):
    TFLITE = "tflite"
    ONNX = "onnx"
    SKLEARN = "sklearn"


class Runtime(str, Enum):
    TFLITE_MICRO = "tflite-micro"
    EMLEARN = "emlearn"
    TFLITE = "tflite"
    TENSORRT = "tensorrt"


class ReportMode(str, Enum):
    SERIAL = "serial"
    HTTP = "http"
    MQTT = "mqtt"


class OutputKind(str, Enum):
    FIRMWARE = "firmware"
    LIBRARY = "library"
    BOTH = "both"


class BuildStatus(str, Enum):
    PENDING = "pending"
    PARSING = "parsing"
    CHECKING = "checking"
    QUANTIZING = "quantizing"
    CONVERTING = "converting"
    COMPILING = "compiling"
    PACKAGING = "packaging"
    COMPLETED = "completed"
    FAILED = "failed"


class DType(str, Enum):
    FLOAT32 = "float32"
    FLOAT16 = "float16"
    INT8 = "int8"
    UINT8 = "uint8"
    INT16 = "int16"
    INT32 = "int32"
