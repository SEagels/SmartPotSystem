/**
 * main.cpp — SmartPot ESP32-S3 固件入口
 *
 * 初始化顺序:
 *   1. Serial + 引脚表
 *   2. WiFi 连接
 *   3. 传感器、摄像头、水泵初始化
 *   4. MQTT + HTTP 上传服务
 *   5. 本地 HTTP 服务器
 *
 * 主循环:
 *   - WiFi 重连 / MQTT 维持 / 指令处理
 *   - 传感器周期采集 (5s)
 *   - 遥测周期上报 (5min)
 *   - 本地自动补水逻辑
 *   - HTTP 请求处理
 */

#include <Arduino.h>
#include <time.h>
#include "config.h"
#include "board_pins.h"
#include "wifi_manager.h"
#include "sensor_service.h"
#include "camera_service.h"
#include "pump_service.h"
#include "upload_service.h"
#include "http_server.h"

// 定时器
static unsigned long s_last_sensor    = 0;
static unsigned long s_last_telemetry = 0;
static unsigned long s_last_status    = 0;

// 自动补水
static bool s_auto_water = true;

static void check_auto_watering() {
    if (!s_auto_water || !pump_can_run()) return;

    SensorData d = sensors_get_latest();
    if (!d.valid) return;
    if (d.temperature > AUTO_WATER_TEMPERATURE_MAX) return;

    if (d.soil_moisture < AUTO_WATER_SOIL_MOISTURE_MIN) {
        Serial.printf("[AutoWater] Soil %.1f%% < %.1f%%\n",
                      d.soil_moisture, AUTO_WATER_SOIL_MOISTURE_MIN);
        float sb = d.soil_moisture;
        uint32_t actual = pump_run(AUTO_WATER_DURATION_MS);
        float sa = soil_moisture_read();
        float ml = pump_estimate_volume(actual);
        upload_watering_event("auto", actual, ml, sb, sa);
    }
}

static void print_pin_map() {
    Serial.println("========================================");
    Serial.println(" SmartPot ESP32-S3  " FIRMWARE_VERSION);
    Serial.println("========================================");
    Serial.println("Camera OV2640:");
    Serial.printf("  D[0..7]=%d,%d,%d,%d,%d,%d,%d,%d\n",
      CAM_PIN_D0,CAM_PIN_D1,CAM_PIN_D2,CAM_PIN_D3,
      CAM_PIN_D4,CAM_PIN_D5,CAM_PIN_D6,CAM_PIN_D7);
    Serial.printf("  XCLK=%d PCLK=%d VSYNC=%d HREF=%d SIOD=%d SIOC=%d\n",
      CAM_PIN_XCLK,CAM_PIN_PCLK,CAM_PIN_VSYNC,CAM_PIN_HREF,
      CAM_PIN_SIOD,CAM_PIN_SIOC);
    Serial.printf("Peripherals: Pump=GPIO%d DHT11=GPIO%d BH1750=SDA%d/SCL%d Soil=GPIO%d(ADC)\n",
      PUMP_PIN_IN, DHT11_PIN_DATA, BH1750_SDA, BH1750_SCL, SOIL_MOISTURE_PIN);
    Serial.printf("Mock: %s | Heap: %d\n",
      MOCK_MODE ? "ON" : "OFF", ESP.getFreeHeap());
    Serial.println("========================================\n");
}

void setup() {
    Serial.begin(115200);
    delay(500);
    print_pin_map();

    wifi_init();
    if (wifi_is_connected()) {
        configTime(NTP_GMT_OFFSET_SEC, NTP_DST_OFFSET_SEC, NTP_SERVER_1, NTP_SERVER_2);
        Serial.printf("[NTP] Syncing time (%s, %s)...\n", NTP_SERVER_1, NTP_SERVER_2);
        struct tm ti;
        int retry = 0;
        int max_retry = NTP_SYNC_TIMEOUT_MS / 500;
        while (!getLocalTime(&ti) && retry++ < max_retry) {
            Serial.print(".");
            delay(500);
        }
        if (retry <= max_retry) {
            Serial.printf(" OK %04d-%02d-%02d %02d:%02d:%02d\n",
                          ti.tm_year + 1900, ti.tm_mon + 1, ti.tm_mday,
                          ti.tm_hour, ti.tm_min, ti.tm_sec);
        } else {
            Serial.println(" FAIL (time sync timeout, will retry in background)");
        }
    }
    sensors_init();
    if (!camera_init())
        Serial.println("*** Camera FAILED! Photo disabled. ***");
    pump_init();
    upload_init();
    http_server_init();

    if (wifi_is_connected()) upload_device_online();

    Serial.println("\n[Setup] Done. Running.\n");
}

void loop() {
    unsigned long now = millis();

    wifi_loop();
    upload_loop();

    if (now - s_last_sensor >= SENSOR_READ_INTERVAL_MS) {
        s_last_sensor = now;
        sensors_read();
    }

    if (now - s_last_telemetry >= TELEMETRY_INTERVAL_MS) {
        s_last_telemetry = now;
        upload_telemetry(sensors_get_latest(), now / 1000);
    }

    http_server_loop();
    check_auto_watering();

    if (now - s_last_status >= 30000) {
        s_last_status = now;
        SensorData s = sensors_get_latest();
        Serial.printf("[Status] U=%ds WiFi=%s RSSI=%d T=%.1f H=%.1f "
                      "Soil=%.1f Light=%.0f Heap=%d MQTT=%s Pump=%s\n",
          now/1000, wifi_is_connected()?"ON":"OFF", wifi_get_rssi(),
          s.temperature, s.humidity, s.soil_moisture, s.light_intensity,
          ESP.getFreeHeap(), upload_mqtt_connected()?"ON":"OFF",
          pump_is_running()?"ON":"OFF");
    }

    delay(10);
}
