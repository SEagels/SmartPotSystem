/**
 * pump_service.cpp — 水泵控制实现 (Keyes130, GPIO47)
 */

#include "pump_service.h"
#include "board_pins.h"
#include "config.h"
#include <Arduino.h>

static bool                s_running       = false;
static uint32_t            s_last_stop_ms  = 0;
static pump_status_cb_t    s_status_cb     = nullptr;

void pump_init() {
    pinMode(PUMP_PIN_IN, OUTPUT);
    digitalWrite(PUMP_PIN_IN, PUMP_ACTIVE_LEVEL == HIGH ? LOW : HIGH);
    s_running = false;
    s_last_stop_ms = millis();
    Serial.println("[Pump] Initialized (GPIO47, Keyes130)");
}

void pump_set_status_callback(pump_status_cb_t cb) {
    s_status_cb = cb;
}

static void _notify_status(bool running) {
    if (s_status_cb) s_status_cb(running);
}

void pump_on() {
    if (!pump_can_run()) {
        Serial.println("[Pump] Cannot start: cooldown active");
        return;
    }
    digitalWrite(PUMP_PIN_IN, PUMP_ACTIVE_LEVEL);
    s_running = true;
    _notify_status(true);
    Serial.println("[Pump] ON");
}

void pump_off() {
    digitalWrite(PUMP_PIN_IN, PUMP_ACTIVE_LEVEL == HIGH ? LOW : HIGH);
    s_running = false;
    s_last_stop_ms = millis();
    _notify_status(false);
    Serial.println("[Pump] OFF");
}

uint32_t pump_run(uint32_t duration_ms) {
    if (!pump_can_run()) {
        Serial.println("[Pump] Run rejected: still in cooldown");
        return 0;
    }
    if (duration_ms > PUMP_MAX_DURATION_MS) {
        duration_ms = PUMP_MAX_DURATION_MS;
    }

#if MOCK_MODE
    Serial.printf("[Pump] MOCK: running for %dms\n", duration_ms);
    s_running = true;
    delay(duration_ms);
    s_running = false;
    s_last_stop_ms = millis();
    return duration_ms;
#else
    pump_on();
    uint32_t start = millis();
    while (millis() - start < duration_ms) {
        delay(100);
    }
    pump_off();
    uint32_t actual = millis() - start;
    Serial.printf("[Pump] Ran for %dms\n", actual);
    return actual;
#endif
}

bool pump_is_running() {
#if MOCK_MODE
    return false;
#else
    return s_running;
#endif
}

bool pump_can_run() {
    return (millis() - s_last_stop_ms) >= PUMP_COOLDOWN_MS;
}

float pump_estimate_volume(uint32_t duration_ms) {
    return (float)duration_ms / 1000.0f * PUMP_FLOW_RATE_ML_PER_S;
}
