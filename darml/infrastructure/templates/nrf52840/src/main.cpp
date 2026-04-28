#include <Arduino.h>
#include "darml.h"
#include "model_data.h"

#define INFERENCE_INTERVAL_MS {{INFERENCE_INTERVAL_MS}}
#define INPUT_SIZE            {{INPUT_SIZE}}
#define OUTPUT_SIZE           {{OUTPUT_SIZE}}

static float input_buf[INPUT_SIZE];
static float output_buf[OUTPUT_SIZE];

void setup() {
    Serial.begin(115200);
    if (darml_init(model_data, model_data_len) != 0) {
        Serial.println("[Darml] Model init failed.");
        while (1) {}
    }
    Serial.println("[Darml] Ready.");
}

void loop() {
    for (int i = 0; i < INPUT_SIZE; ++i) input_buf[i] = 0.0f;
    darml_infer(input_buf, output_buf, OUTPUT_SIZE);
    Serial.print("[Darml] pred=");
    Serial.print(darml_argmax());
    Serial.print(" conf=");
    Serial.println(darml_confidence(), 3);
    delay(INFERENCE_INTERVAL_MS);
}
