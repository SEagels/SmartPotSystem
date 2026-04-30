/**
 * mock_service.cpp — Mock 模式实现
 * MOCK_MODE=1 时模拟所有硬件外设
 */

#include "mock_service.h"
#include "config.h"
#include <Arduino.h>
#include <cstdlib>

static float s_mock_temp  = 25.3f;
static float s_mock_humid = 65.0f;
static float s_mock_soil  = 42.0f;
static float s_mock_light = 850.0f;

SensorData mock_sensors_read() {
    s_mock_temp  += (random(-10, 11) / 100.0f);
    s_mock_humid += (random(-20, 21) / 100.0f);
    s_mock_soil  += (random(-15, 16) / 100.0f);
    s_mock_light += (random(-50, 51) / 10.0f);

    s_mock_temp  = constrain(s_mock_temp,  15.0f, 35.0f);
    s_mock_humid = constrain(s_mock_humid, 30.0f, 90.0f);
    s_mock_soil  = constrain(s_mock_soil,  15.0f, 75.0f);
    s_mock_light = constrain(s_mock_light,  0.0f, 5000.0f);

    SensorData data;
    data.temperature     = s_mock_temp;
    data.humidity        = s_mock_humid;
    data.soil_moisture   = s_mock_soil;
    data.light_intensity = s_mock_light;
    data.valid           = true;

    Serial.printf("[Mock] T=%.1f H=%.1f Soil=%.1f Light=%.0f\n",
                  data.temperature, data.humidity,
                  data.soil_moisture, data.light_intensity);
    return data;
}

float mock_soil_moisture() {
    s_mock_soil += (random(-10, 11) / 100.0f);
    s_mock_soil = constrain(s_mock_soil, 15.0f, 75.0f);
    return s_mock_soil;
}

// 最小合法 JPEG (1x1 灰色像素)
void mock_generate_jpeg(uint8_t** buf, size_t* len) {
    static const uint8_t MINI_JPEG[] = {
        0xFF, 0xD8,                     // SOI
        0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46,
        0x00, 0x01, 0x01, 0x00, 0x00, 0x01, 0x00, 0x01,
        0x00, 0x00,
        0xFF, 0xDB, 0x00, 0x43, 0x00, // DQT
        0x10, 0x0B, 0x0C, 0x0E, 0x0C, 0x0A, 0x10, 0x0E,
        0x0D, 0x0E, 0x12, 0x11, 0x10, 0x13, 0x18, 0x28,
        0x1A, 0x18, 0x16, 0x16, 0x18, 0x31, 0x23, 0x25,
        0x1D, 0x28, 0x3A, 0x33, 0x3D, 0x3C, 0x39, 0x33,
        0x38, 0x37, 0x40, 0x48, 0x5C, 0x4E, 0x40, 0x44,
        0x57, 0x45, 0x37, 0x38, 0x50, 0x6D, 0x51, 0x57,
        0x5F, 0x62, 0x67, 0x68, 0x67, 0x3E, 0x4D, 0x71,
        0x79, 0x70, 0x64, 0x78, 0x5C, 0x65, 0x67, 0x63,
        0xFF, 0xC0, 0x00, 0x0B, 0x08, 0x00, 0x01, 0x00,
        0x01, 0x01, 0x01, 0x11, 0x00,   // SOF0
        0xFF, 0xC4, 0x00, 0x1F, 0x00, 0x00, 0x01, 0x05,
        0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x02,
        0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A,
        0x0B,                             // DHT
        0xFF, 0xDA, 0x00, 0x08, 0x01, 0x01, 0x00, 0x00,
        0x3F, 0x00,                       // SOS
        0x7F, 0x00,                       // compressed data
        0xFF, 0xD9                        // EOI
    };

    *len = sizeof(MINI_JPEG);
    *buf = (uint8_t*)malloc(*len);
    if (*buf) memcpy(*buf, MINI_JPEG, *len);
    Serial.printf("[Mock] Generated %d-byte JPEG\n", *len);
}

bool mock_camera_capture(CameraFrame& frame) {
    mock_generate_jpeg(&frame.buf, &frame.len);
    frame.width  = 640;
    frame.height = 480;
    frame.quality = 0.75f;
    return true;
}

bool mock_camera_capture_best(int burst_count, CameraFrame& frame) {
    mock_generate_jpeg(&frame.buf, &frame.len);
    frame.width  = 640;
    frame.height = 480;
    frame.quality = 0.70f + (random(0, 20) / 100.0f);
    Serial.printf("[Mock] Burst %d, best q=%.2f\n", burst_count, frame.quality);
    return true;
}
