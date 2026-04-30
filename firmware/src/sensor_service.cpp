/**
 * sensor_service.cpp — 传感器采集实现
 *
 * DHT11 (GPIO21), BH1750 (I2C: SDA=41, SCL=42), 土壤湿度 ADC (GPIO1)
 */

#include "sensor_service.h"
#include "board_pins.h"
#include "config.h"
#include "mock_service.h"
#include <Arduino.h>

#if !MOCK_MODE
#include <DHT.h>
#include <BH1750.h>
#include <Wire.h>

static DHT    s_dht(DHT11_PIN_DATA, DHT11);
static BH1750 s_bh1750;
#endif

static SensorData s_latest;

void sensors_init() {
    s_latest = {0, 0, 0, 0, false};

#if MOCK_MODE
    Serial.println("[Sensors] MOCK MODE initialized");
#else
    s_dht.begin();
    Serial.println("[Sensors] DHT11 initialized (GPIO21)");

    Wire.begin(BH1750_SDA, BH1750_SCL);
    bool bh_ok = s_bh1750.begin(BH1750::CONTINUOUS_HIGH_RES_MODE, 0x23, &Wire);
    Serial.printf("[Sensors] BH1750 init (SDA=41,SCL=42): %s\n", bh_ok ? "OK" : "FAIL");

    analogReadResolution(12);
    analogSetAttenuation(ADC_11db);
    pinMode(SOIL_MOISTURE_PIN, INPUT);
    Serial.println("[Sensors] Soil moisture ADC ready (GPIO1, ADC1_CH0)");
#endif
}

SensorData sensors_read() {
#if MOCK_MODE
    s_latest = mock_sensors_read();
    return s_latest;
#else
    SensorData data;
    float t = 0, h = 0;

    if (dht11_read(t, h)) {
        data.temperature = t;
        data.humidity = h;
    } else {
        data.temperature = s_latest.temperature;
        data.humidity = s_latest.humidity;
    }

    float lux = bh1750_read();
    data.light_intensity = (lux >= 0) ? lux : s_latest.light_intensity;
    data.soil_moisture = soil_moisture_read();

    data.valid = (data.temperature > -40 && data.temperature < 85 &&
                  data.humidity >= 0 && data.humidity <= 100);
    s_latest = data;

    Serial.printf("[Sensors] T=%.1fC H=%.1f%% Soil=%.1f%% Light=%.0flux\n",
                  data.temperature, data.humidity,
                  data.soil_moisture, data.light_intensity);
    return data;
#endif
}

float soil_moisture_read() {
#if MOCK_MODE
    return mock_soil_moisture();
#else
    int raw = analogRead(SOIL_MOISTURE_PIN);
    float pct = (1.0f - (float)raw / 4095.0f) * 100.0f;
    return constrain(pct, 0.0f, 100.0f);
#endif
}

bool dht11_read(float& temperature, float& humidity) {
#if MOCK_MODE
    SensorData d = mock_sensors_read();
    temperature = d.temperature;
    humidity = d.humidity;
    return true;
#else
    float t = s_dht.readTemperature();
    float h = s_dht.readHumidity();
    if (isnan(t) || isnan(h)) {
        Serial.println("[DHT11] Read failed");
        return false;
    }
    temperature = t;
    humidity = h;
    return true;
#endif
}

float bh1750_read() {
#if MOCK_MODE
    return mock_sensors_read().light_intensity;
#else
    float lux = s_bh1750.readLightLevel();
    if (lux < 0) {
        Serial.println("[BH1750] Read failed");
        return -1.0f;
    }
    return lux;
#endif
}

SensorData sensors_get_latest() {
    return s_latest;
}
