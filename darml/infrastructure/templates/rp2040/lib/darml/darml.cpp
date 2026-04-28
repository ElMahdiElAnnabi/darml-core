// Darml inference wrapper — STM32 via tflm_cortexm + eloquent_tinyml.
// Mirrors the ESP32 wrapper; only the runtime header differs.

#include "darml.h"

#include <Arduino.h>
#include <tflm_cortexm.h>

// EloquentTinyML's tf.h uses ESP_LOGI (ESP-IDF logging) inside template
// methods. On STM32 the macro doesn't exist, so we stub it to a no-op
// before including the wrapper.
#ifndef ESP_LOGI
#define ESP_LOGI(tag, ...)  ((void)0)
#endif

#include <eloquent_tinyml.h>

#define DARML_INPUT_SIZE   {{INPUT_SIZE}}
#define DARML_OUTPUT_SIZE  {{OUTPUT_SIZE}}
#define DARML_ARENA_SIZE   {{TENSOR_ARENA_SIZE}}

namespace {
// 128 covers every op MicroMutableOpResolver exposes today (~99 unique).
constexpr int kNumOps = 128;
Eloquent::TF::Sequential<kNumOps, DARML_ARENA_SIZE> g_tf;
bool      g_ready       = false;
int       g_argmax      = 0;
float     g_confidence  = 0.0f;
uint32_t  g_latency_us  = 0;

// Approximates the AllOpsResolver behavior — register every op the
// underlying MicroMutableOpResolver supports.
void register_ops() {
    auto& r = g_tf.resolver;
    r.AddAbs();                          r.AddAdd();
    r.AddAddN();                         r.AddArgMax();
    r.AddArgMin();                       r.AddAssignVariable();
    r.AddAveragePool2D();                r.AddBatchToSpaceNd();
    r.AddBroadcastArgs();                r.AddBroadcastTo();
    r.AddCallOnce();                     r.AddCast();
    r.AddCeil();                         r.AddCircularBuffer();
    r.AddConcatenation();                r.AddConv2D();
    r.AddCos();                          r.AddCumSum();
    r.AddDepthToSpace();                 r.AddDepthwiseConv2D();
    r.AddDequantize();                   r.AddDetectionPostprocess();
    r.AddDiv();                          r.AddElu();
    r.AddEqual();                        r.AddEthosU();
    r.AddExp();                          r.AddExpandDims();
    r.AddFill();                         r.AddFloor();
    r.AddFloorDiv();                     r.AddFloorMod();
    r.AddFullyConnected();               r.AddGather();
    r.AddGatherNd();                     r.AddGreater();
    r.AddGreaterEqual();                 r.AddHardSwish();
    r.AddIf();                           r.AddL2Normalization();
    r.AddL2Pool2D();                     r.AddLeakyRelu();
    r.AddLess();                         r.AddLessEqual();
    r.AddLog();                          r.AddLogicalAnd();
    r.AddLogicalNot();                   r.AddLogicalOr();
    r.AddLogistic();                     r.AddLogSoftmax();
    r.AddMaxPool2D();                    r.AddMaximum();
    r.AddMean();                         r.AddMinimum();
    r.AddMirrorPad();                    r.AddMul();
    r.AddNeg();                          r.AddNotEqual();
    r.AddPack();                         r.AddPadV2();
    r.AddPrelu();                        r.AddQuantize();
    r.AddReadVariable();                 r.AddReduceMax();
    r.AddRelu();                         r.AddRelu6();
    r.AddReshape();                      r.AddResizeBilinear();
    r.AddResizeNearestNeighbor();        r.AddRound();
    r.AddRsqrt();                        r.AddSelectV2();
    r.AddShape();                        r.AddSin();
    r.AddSlice();                        r.AddSoftmax();
    r.AddSpaceToBatchNd();               r.AddSpaceToDepth();
    r.AddSplit();                        r.AddSplitV();
    r.AddSqrt();                         r.AddSquare();
    r.AddSquaredDifference();            r.AddSqueeze();
    r.AddStridedSlice();                 r.AddSub();
    r.AddSum();                          r.AddTanh();
    r.AddTranspose();                    r.AddTransposeConv();
    r.AddUnidirectionalSequenceLSTM();   r.AddUnpack();
    r.AddVarHandle();                    r.AddWhile();
    r.AddZerosLike();
}
}  // namespace

extern "C" int darml_init(const unsigned char* model_bytes, unsigned int /*model_size*/) {
    g_tf.setNumInputs(DARML_INPUT_SIZE);
    g_tf.setNumOutputs(DARML_OUTPUT_SIZE);
    register_ops();
    if (!g_tf.begin(const_cast<uint8_t*>(model_bytes)).isOk()) {
        return -1;
    }
    g_ready = true;
    return 0;
}

extern "C" int darml_infer(const void* input, float* output, int output_size) {
    if (!g_ready) return -1;
    const float* in_f = static_cast<const float*>(input);
    if (!g_tf.predict(const_cast<float*>(in_f)).isOk()) return -1;
    g_latency_us = static_cast<uint32_t>(g_tf.benchmark.microseconds());

    const int copy = output_size < DARML_OUTPUT_SIZE ? output_size : DARML_OUTPUT_SIZE;
    int   best_i = 0;
    float best_v = g_tf.output(0);
    output[0] = best_v;
    for (int i = 1; i < copy; ++i) {
        const float v = g_tf.output(i);
        output[i] = v;
        if (v > best_v) { best_v = v; best_i = i; }
    }
    g_argmax     = best_i;
    g_confidence = best_v;
    return 0;
}

extern "C" int         darml_argmax(void)       { return g_argmax; }
extern "C" float       darml_confidence(void)   { return g_confidence; }
extern "C" uint32_t    darml_latency_us(void)   { return g_latency_us; }
extern "C" const char* darml_model_format(void) { return "tflite"; }
extern "C" int         darml_input_size(void)   { return DARML_INPUT_SIZE; }
extern "C" int         darml_output_size(void)  { return DARML_OUTPUT_SIZE; }

// TFLite Micro's micro_log.cpp expects a platform-provided DebugLog symbol.
// On ESP32, tflm_esp32 ships it; on Cortex-M, we provide our own. Route to
// Serial when available; degrade silently otherwise.
extern "C" void DebugLog(const char* s) {
    if (Serial) Serial.print(s);
}
