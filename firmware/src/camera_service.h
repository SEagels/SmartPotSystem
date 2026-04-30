/**
 * camera_service.h — OV2640 摄像头服务
 */

#ifndef CAMERA_SERVICE_H
#define CAMERA_SERVICE_H

#include <stdint.h>
#include <stddef.h>

struct CameraFrame {
    uint8_t* buf;
    size_t   len;
    int      width;
    int      height;
    float    quality;
};

bool  camera_init();
bool  camera_capture(CameraFrame& frame);
void  camera_frame_free(CameraFrame& frame);
bool  camera_capture_best(int burst_count, CameraFrame& frame);
float camera_quality_score(const uint8_t* buf, int width, int height);
void  camera_led_on();
void  camera_led_off();

#endif
