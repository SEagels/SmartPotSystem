/**
 * pump_service.h — Keyes130 水泵控制 (GPIO47)
 */

#ifndef PUMP_SERVICE_H
#define PUMP_SERVICE_H

#include <stdint.h>

void     pump_init();
void     pump_on();
void     pump_off();
uint32_t pump_run(uint32_t duration_ms);
bool     pump_is_running();
bool     pump_can_run();
float    pump_estimate_volume(uint32_t duration_ms);

#endif
