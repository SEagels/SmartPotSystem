#include "runtime_config.h"
#include "config.h"
#include <Arduino.h>

#ifndef AUTO_WATER_ENABLED_DEFAULT
#define AUTO_WATER_ENABLED_DEFAULT false
#endif

static bool s_auto_water_enabled = AUTO_WATER_ENABLED_DEFAULT;
static float s_auto_water_soil_moisture_min = AUTO_WATER_SOIL_MOISTURE_MIN;
static float s_auto_water_temperature_max = AUTO_WATER_TEMPERATURE_MAX;
static uint32_t s_auto_water_duration_ms = AUTO_WATER_DURATION_MS;

void runtime_config_init() {
    s_auto_water_enabled = AUTO_WATER_ENABLED_DEFAULT;
    s_auto_water_soil_moisture_min = AUTO_WATER_SOIL_MOISTURE_MIN;
    s_auto_water_temperature_max = AUTO_WATER_TEMPERATURE_MAX;
    s_auto_water_duration_ms = AUTO_WATER_DURATION_MS;
    Serial.printf("[RuntimeConfig] auto_water=%s soil_min=%.1f%% temp_max=%.1fC duration=%ums\n",
                  s_auto_water_enabled ? "ON" : "OFF",
                  s_auto_water_soil_moisture_min,
                  s_auto_water_temperature_max,
                  s_auto_water_duration_ms);
}

bool runtime_auto_water_enabled() {
    return s_auto_water_enabled;
}

float runtime_auto_water_soil_moisture_min() {
    return s_auto_water_soil_moisture_min;
}

float runtime_auto_water_temperature_max() {
    return s_auto_water_temperature_max;
}

uint32_t runtime_auto_water_duration_ms() {
    return s_auto_water_duration_ms;
}

void runtime_set_auto_water_enabled(bool enabled) {
    s_auto_water_enabled = enabled;
}

void runtime_set_auto_water_soil_moisture_min(float value) {
    s_auto_water_soil_moisture_min = constrain(value, 0.0f, 100.0f);
}

void runtime_set_auto_water_temperature_max(float value) {
    s_auto_water_temperature_max = constrain(value, 0.0f, 80.0f);
}

void runtime_set_auto_water_duration_ms(uint32_t value) {
    s_auto_water_duration_ms = constrain(value, (uint32_t)1000, (uint32_t)PUMP_MAX_DURATION_MS);
}
