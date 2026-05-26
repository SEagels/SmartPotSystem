/**
 * Public SmartPot firmware configuration.
 *
 * This file is intentionally safe to commit. Fill these values locally before
 * flashing, or copy it to an ignored local variant if you adapt the firmware to
 * include private credentials from a separate header.
 */

#ifndef CONFIG_H
#define CONFIG_H

#include <stdint.h>

// ============================================================
// Build mode
// ============================================================

#define MOCK_MODE           1   // 1=no-hardware mock mode, 0=real hardware

// ============================================================
// Device identity
// ============================================================

#define DEVICE_ID           "SP000001"
#define FIRMWARE_VERSION    "v1.0.1-public"

// ============================================================
// WiFi configuration
// ============================================================

#define WIFI_SSID           "YOUR_WIFI_SSID"
#define WIFI_PASSWORD       "YOUR_WIFI_PASSWORD"
#define WIFI_CONNECT_TIMEOUT_MS   15000
#define WIFI_RETRY_INTERVAL_MS    30000

// ============================================================
// Cloud API configuration
// ============================================================

#define CLOUD_API_HOST      "192.168.1.100"
#define CLOUD_API_PORT      8000
#define CLOUD_API_BASE_URL  "http://192.168.1.100:8000/v1"
#define CLOUD_API_TOKEN     "CHANGE_ME_DEVICE_TOKEN"

// ============================================================
// MQTT configuration
// ============================================================

#define MQTT_BROKER_HOST    "192.168.1.100"
#define MQTT_BROKER_PORT    1883
#define MQTT_MAX_PACKET_SIZE 1024
#define MQTT_USERNAME       ""
#define MQTT_PASSWORD       ""
#define MQTT_CLIENT_ID      DEVICE_ID
#define MQTT_KEEPALIVE_S    60
#define MQTT_RECONNECT_INTERVAL_MS  5000
#define MQTT_STATUS_INTERVAL_MS     30000

// MQTT topic templates
#define MQTT_TOPIC_TELEMETRY       "smartpot/" DEVICE_ID "/telemetry"
#define MQTT_TOPIC_IMAGE_UPLOADED  "smartpot/" DEVICE_ID "/image/uploaded"
#define MQTT_TOPIC_IMAGE_RESULT    "smartpot/" DEVICE_ID "/image/result"
#define MQTT_TOPIC_EVENT_WATERING  "smartpot/" DEVICE_ID "/event/watering"
#define MQTT_TOPIC_EVENT_ALARM     "smartpot/" DEVICE_ID "/event/alarm"
#define MQTT_TOPIC_COMMAND_WATER   "smartpot/" DEVICE_ID "/command/water"
#define MQTT_TOPIC_COMMAND_PHOTO   "smartpot/" DEVICE_ID "/command/photo"
#define MQTT_TOPIC_COMMAND_CONFIG  "smartpot/" DEVICE_ID "/command/config"
#define MQTT_TOPIC_COMMAND_SYNC    "smartpot/" DEVICE_ID "/command/sync"
#define MQTT_TOPIC_RESPONSE_WATER  "smartpot/" DEVICE_ID "/response/water"
#define MQTT_TOPIC_RESPONSE_PHOTO  "smartpot/" DEVICE_ID "/response/photo"
#define MQTT_TOPIC_RESPONSE_CONFIG "smartpot/" DEVICE_ID "/response/config"
#define MQTT_TOPIC_RESPONSE_SYNC   "smartpot/" DEVICE_ID "/response/sync"
#define MQTT_TOPIC_STATUS          "smartpot/" DEVICE_ID "/status"

// ============================================================
// NTP configuration
// ============================================================

#define NTP_SERVER_1        "ntp.aliyun.com"
#define NTP_SERVER_2        "ntp.ntsc.ac.cn"
#define NTP_GMT_OFFSET_SEC  28800
#define NTP_DST_OFFSET_SEC  0
#define NTP_SYNC_TIMEOUT_MS 5000

// ============================================================
// Sensor intervals
// ============================================================

#define TELEMETRY_INTERVAL_MS      300000
#define SENSOR_READ_INTERVAL_MS    5000

// ============================================================
// Pump configuration
// ============================================================

#define PUMP_ACTIVE_LEVEL           HIGH
#define PUMP_MAX_DURATION_MS        30000
#define PUMP_COOLDOWN_MS            10000
#define PUMP_FLOW_RATE_ML_PER_S     10

// ============================================================
// Camera configuration
// ============================================================

#define CAMERA_FRAME_SIZE           FRAMESIZE_UXGA
#define CAMERA_JPEG_QUALITY         12
#define CAMERA_BRIGHTNESS           0

// ============================================================
// Local fallback auto-watering thresholds
// ============================================================

#define AUTO_WATER_SOIL_MOISTURE_MIN   25.0f
#define AUTO_WATER_TEMPERATURE_MAX     38.0f
#define AUTO_WATER_DURATION_MS         8000

// ============================================================
// Local HTTP server
// ============================================================

#define LOCAL_HTTP_PORT         80

// ============================================================
// Water tank
// ============================================================

#define WATER_TANK_CAPACITY_ML  2000

#endif // CONFIG_H
