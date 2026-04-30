/**
 * mock_service.h — Mock 模式 (MOCK_MODE=1)
 * 模拟摄像头、传感器、ADC 数据
 */

#ifndef MOCK_SERVICE_H
#define MOCK_SERVICE_H

#include "sensor_service.h"
#include "camera_service.h"

SensorData mock_sensors_read();
bool      mock_camera_capture(CameraFrame& frame);
bool      mock_camera_capture_best(int burst_count, CameraFrame& frame);
float     mock_soil_moisture();
void      mock_generate_jpeg(uint8_t** buf, size_t* len);

#endif
