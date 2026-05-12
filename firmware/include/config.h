/**
 * config.h — SmartPot 固件全局配置
 *
 * 所有可调参数集中在此文件。
 */

#ifndef CONFIG_H
#define CONFIG_H

#include <stdint.h>

// ============================================================
// 编译模式
// ============================================================

#define MOCK_MODE           0   // 1=Mock模式(无硬件运行), 0=真实硬件

// ============================================================
// 设备身份
// ============================================================

#define DEVICE_ID           "SP000001"        // 设备唯一 ID (出厂烧录)
#define FIRMWARE_VERSION    "v1.0.0"

// ============================================================
// WiFi 配置
// ============================================================

#define WIFI_SSID           "YOUR_WIFI_SSID"
#define WIFI_PASSWORD       "YOUR_WIFI_PASSWORD"
#define WIFI_CONNECT_TIMEOUT_MS   15000       // 连接超时
#define WIFI_RETRY_INTERVAL_MS    30000       // 连接失败后重试间隔

// ============================================================
// 云端服务器配置
// ============================================================

#define CLOUD_API_HOST      "192.168.1.100"
#define CLOUD_API_PORT      8000
#define CLOUD_API_BASE_URL  "http://192.168.1.100:8000/v1"
#define CLOUD_API_TOKEN     "CHANGE_ME_DEVICE_TOKEN"

// ============================================================
// MQTT 配置
// ============================================================

#define MQTT_BROKER_HOST    "192.168.1.100"
#define MQTT_BROKER_PORT    1883
#define MQTT_MAX_PACKET_SIZE 1024       // PubSubClient 默认128字节不够JSON遥测包
#define MQTT_USERNAME       ""
#define MQTT_PASSWORD       ""
#define MQTT_CLIENT_ID      DEVICE_ID
#define MQTT_KEEPALIVE_S    60
#define MQTT_RECONNECT_INTERVAL_MS  5000

// MQTT 主题模板
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
// NTP 对时配置
// ============================================================

#define NTP_SERVER_1        "ntp.aliyun.com"
#define NTP_SERVER_2        "ntp.ntsc.ac.cn"
#define NTP_GMT_OFFSET_SEC  28800       // UTC+8 (北京时间)
#define NTP_DST_OFFSET_SEC  0           // 中国不实行夏令时
#define NTP_SYNC_TIMEOUT_MS 5000        // 首次对时等待超时

// ============================================================
// 传感器采集周期
// ============================================================

#define TELEMETRY_INTERVAL_MS      300000      // 遥测上报间隔 (默认 5 分钟)
#define SENSOR_READ_INTERVAL_MS    5000        // 传感器读取间隔 (5 秒)

// ============================================================
// 水泵配置
// ============================================================

#define PUMP_ACTIVE_LEVEL           HIGH       // HIGH=active_high, LOW=active_low
#define PUMP_MAX_DURATION_MS        30000      // 单次最大运行时长
#define PUMP_COOLDOWN_MS            10000      // 两次补水最小间隔 (10 秒)
#define PUMP_FLOW_RATE_ML_PER_S     10         // 水泵流量 (mL/s, 近似值)

// ============================================================
// 摄像头配置
// ============================================================

#define CAMERA_FRAME_SIZE           FRAMESIZE_UXGA   // 1600x1200
#define CAMERA_JPEG_QUALITY         12               // 0-63, 越小质量越高
#define CAMERA_BRIGHTNESS           0                // -2 to 2

// ============================================================
// 自动补水阈值（无云端指令时的本地保守值）
// ============================================================

#define AUTO_WATER_SOIL_MOISTURE_MIN   25.0f   // 土壤湿度低于此值触发补水
#define AUTO_WATER_TEMPERATURE_MAX     38.0f   // 温度过高时不补水（防烫伤）
#define AUTO_WATER_DURATION_MS         8000    // 默认补水时长

// ============================================================
// 本地 HTTP 服务器
// ============================================================

#define LOCAL_HTTP_PORT         80

// ============================================================
// 水箱
// ============================================================

#define WATER_TANK_CAPACITY_ML  2000        // 水箱总容量 (mL)

#endif // CONFIG_H
