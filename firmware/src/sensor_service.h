/**
 * sensor_service.h — DHT11 + BH1750 + 土壤湿度传感器采集
 */

#ifndef SENSOR_SERVICE_H
#define SENSOR_SERVICE_H

#include <stdint.h>

struct SensorData {
    float temperature;
    float humidity;
    float soil_moisture;
    float light_intensity;
    bool  valid;
};

void      sensors_init();
SensorData sensors_read();
float     soil_moisture_read();
bool      dht11_read(float& temperature, float& humidity);
float     bh1750_read();
SensorData sensors_get_latest();

#endif
