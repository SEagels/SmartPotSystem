/**
 * upload_service.h — MQTT + HTTPS 数据上传服务
 */

#ifndef UPLOAD_SERVICE_H
#define UPLOAD_SERVICE_H

#include "sensor_service.h"
#include "camera_service.h"
#include <stdint.h>

void upload_init();
void upload_loop();
void upload_telemetry(const SensorData& data, uint32_t uptime_s);
bool upload_image(const CameraFrame& frame, int photo_index, int burst_total);
void upload_watering_event(const char* trigger, uint32_t duration_ms,
                           float water_ml, float soil_before, float soil_after);
void upload_cmd_response(const char* cmd_id, const char* status,
                         const char* detail);
void upload_pump_status(bool running);
void upload_device_online();
bool upload_mqtt_connected();

#endif
