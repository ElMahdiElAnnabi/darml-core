#ifndef DARML_H
#define DARML_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
int      darml_init(const unsigned char* model_data, unsigned int model_size);
int      darml_infer(const void* input, float* output, int output_size);
int      darml_argmax(void);
float    darml_confidence(void);
uint32_t darml_latency_us(void);
const char* darml_model_format(void);
int      darml_input_size(void);
int      darml_output_size(void);
#ifdef __cplusplus
}
#endif
#endif
