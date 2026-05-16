#ifndef RUNTIME_CONFIG_H
#define RUNTIME_CONFIG_H

#include <stdint.h>

void runtime_config_init();

bool runtime_auto_water_enabled();
float runtime_auto_water_soil_moisture_min();
float runtime_auto_water_temperature_max();
uint32_t runtime_auto_water_duration_ms();

void runtime_set_auto_water_enabled(bool enabled);
void runtime_set_auto_water_soil_moisture_min(float value);
void runtime_set_auto_water_temperature_max(float value);
void runtime_set_auto_water_duration_ms(uint32_t value);

#endif
