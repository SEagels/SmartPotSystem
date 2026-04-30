/**
 * camera_service.cpp — OV2640 摄像头服务
 * 严格使用 board_pins.h 手动引脚映射，不使用默认宏
 */

#include "camera_service.h"
#include "board_pins.h"
#include "config.h"
#include "mock_service.h"
#include <Arduino.h>

#if !MOCK_MODE
#include "esp_camera.h"
#include <Adafruit_NeoPixel.h>

static camera_config_t build_camera_config() {
    camera_config_t cfg;
    cfg.ledc_channel = LEDC_CHANNEL_0;
    cfg.ledc_timer   = LEDC_TIMER_0;

    cfg.pin_d0 = CAM_PIN_D0; cfg.pin_d1 = CAM_PIN_D1;
    cfg.pin_d2 = CAM_PIN_D2; cfg.pin_d3 = CAM_PIN_D3;
    cfg.pin_d4 = CAM_PIN_D4; cfg.pin_d5 = CAM_PIN_D5;
    cfg.pin_d6 = CAM_PIN_D6; cfg.pin_d7 = CAM_PIN_D7;

    cfg.pin_xclk  = CAM_PIN_XCLK;
    cfg.pin_pclk  = CAM_PIN_PCLK;
    cfg.pin_vsync = CAM_PIN_VSYNC;
    cfg.pin_href  = CAM_PIN_HREF;

    cfg.pin_sscb_sda = CAM_PIN_SIOD;
    cfg.pin_sscb_scl = CAM_PIN_SIOC;
    cfg.pin_pwdn     = CAM_PIN_PWDN;
    cfg.pin_reset    = CAM_PIN_RESET;

    cfg.xclk_freq_hz = 20000000;
    cfg.pixel_format = PIXFORMAT_JPEG;
    cfg.frame_size   = CAMERA_FRAME_SIZE;
    cfg.jpeg_quality = CAMERA_JPEG_QUALITY;
    cfg.fb_count     = 2;
    cfg.grab_mode    = CAMERA_GRAB_WHEN_EMPTY;

    cfg.fb_location = psramFound() ? CAMERA_FB_IN_PSRAM : CAMERA_FB_IN_DRAM;
    cfg.fb_count    = psramFound() ? 2 : 1;

    return cfg;
}

static Adafruit_NeoPixel s_strip(1, WS2812B_PIN, NEO_GRB + NEO_KHZ800);
#endif // !MOCK_MODE

static bool s_initialized = false;

bool camera_init() {
#if MOCK_MODE
    Serial.println("[Camera] MOCK MODE initialized");
    s_initialized = true;
    return true;
#else
    camera_config_t cfg = build_camera_config();
    esp_err_t err = esp_camera_init(&cfg);
    if (err != ESP_OK) {
        Serial.printf("[Camera] Init failed: 0x%x\n", err);
        return false;
    }

    sensor_t* s = esp_camera_sensor_get();
    if (s) {
        s->set_brightness(s, CAMERA_BRIGHTNESS);
        s->set_whitebal(s, 1);
        s->set_awb_gain(s, 1);
        s->set_exposure_ctrl(s, 1);
        s->set_gain_ctrl(s, 1);
    }

    s_strip.begin();
    s_strip.clear();
    s_strip.show();
    s_initialized = true;
    Serial.println("[Camera] OV2640 ready (manual pin config)");
    return true;
#endif
}

bool camera_capture(CameraFrame& frame) {
#if MOCK_MODE
    return mock_camera_capture(frame);
#else
    if (!s_initialized) return false;

    camera_fb_t* fb = esp_camera_fb_get();
    if (!fb) { Serial.println("[Camera] Capture failed"); return false; }

    frame.buf = (uint8_t*)malloc(fb->len);
    if (!frame.buf) { esp_camera_fb_return(fb); return false; }

    memcpy(frame.buf, fb->buf, fb->len);
    frame.len = fb->len;
    frame.width = fb->width;
    frame.height = fb->height;
    frame.quality = constrain((float)fb->len / (float)(fb->width * fb->height) * 10.0f, 0.0f, 1.0f);

    esp_camera_fb_return(fb);
    Serial.printf("[Camera] %dx%d %d bytes q=%.2f\n",
                  frame.width, frame.height, frame.len, frame.quality);
    return true;
#endif
}

void camera_frame_free(CameraFrame& frame) {
    if (frame.buf) { free(frame.buf); frame.buf = nullptr; frame.len = 0; }
}

void camera_led_on() {
#if !MOCK_MODE
    s_strip.setPixelColor(0, s_strip.Color(255, 220, 180));
    s_strip.show();
#endif
}

void camera_led_off() {
#if !MOCK_MODE
    s_strip.clear();
    s_strip.show();
#endif
}

bool camera_capture_best(int burst_count, CameraFrame& frame) {
#if MOCK_MODE
    return mock_camera_capture_best(burst_count, frame);
#else
    camera_led_on();
    delay(50);

    CameraFrame best = {nullptr, 0, 0, 0, -1.0f};
    for (int i = 0; i < burst_count; i++) {
        CameraFrame cur;
        if (!camera_capture(cur)) continue;
        if (cur.quality > best.quality) {
            camera_frame_free(best);
            best = cur;
        } else {
            camera_frame_free(cur);
        }
    }

    camera_led_off();

    if (!best.buf) return false;
    frame = best;
    return true;
#endif
}

float camera_quality_score(const uint8_t* buf, int width, int height) {
    if (!buf || width < 3 || height < 3) return 0.0f;
    float sum = 0.0f;
    int count = 0;
    for (int y = 1; y < height - 1; y++) {
        for (int x = 1; x < width - 1; x++) {
            int idx = y * width + x;
            int lap = 4 * buf[idx] - buf[idx-1] - buf[idx+1]
                      - buf[idx-width] - buf[idx+width];
            sum += (float)(lap * lap);
            count++;
        }
    }
    return constrain((count > 0 ? sum / count : 0.0f) / 10000.0f, 0.0f, 1.0f);
}
