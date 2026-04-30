/**
 * board_pins.h — SmartPot ESP32-S3 引脚定义
 *
 * 本文件严格定义所有 GPIO 分配，不允许修改。
 * 引脚分为三组：已占用（摄像头）、禁止使用、允许使用。
 */

#ifndef BOARD_PINS_H
#define BOARD_PINS_H

// ============================================================
// 一、OV2640 摄像头引脚（全部已被占用，禁止用于其他用途）
// ============================================================

#define CAM_PIN_PWDN    -1   // 未连接
#define CAM_PIN_RESET   -1   // 未连接
#define CAM_PIN_XCLK    15   // XCLK (外部时钟)
#define CAM_PIN_SIOD    4    // SDA (SCCB 数据)
#define CAM_PIN_SIOC    5    // SCL (SCCB 时钟)

#define CAM_PIN_D7      16   // Y9
#define CAM_PIN_D6      17   // Y8
#define CAM_PIN_D5      18   // Y7
#define CAM_PIN_D4      12   // Y6
#define CAM_PIN_D3      10   // Y5
#define CAM_PIN_D2      8    // Y4
#define CAM_PIN_D1      9    // Y3
#define CAM_PIN_D0      11   // Y2

#define CAM_PIN_VSYNC   6    // VSYNC
#define CAM_PIN_HREF    7    // HREF
#define CAM_PIN_PCLK    13   // PCLK

// ============================================================
// 二、外设 GPIO 分配（仅使用允许列表中的引脚）
// ============================================================

// 水泵驱动模块 (Keyes130)
#define PUMP_PIN_IN     47   // 水泵 IN+

// DHT11 温湿度传感器
#define DHT11_PIN_DATA  21   // 单总线数据

// BH1750 光照传感器 (I2C)
#define BH1750_SDA      41
#define BH1750_SCL      42

// 土壤湿度传感器 (ADC)
#define SOIL_MOISTURE_PIN  1   // ADC1_CH0, AO 输出 0~100%

// WS2812B 补光灯珠
#define WS2812B_PIN        48  // 单总线 RGB LED

// ============================================================
// 三、禁止使用的 GPIO（列出以供参考，代码中不得使用）
// ============================================================
//
// GPIO0   — Boot 引脚
// GPIO19  — USB D-
// GPIO20  — USB D+
// GPIO38  — SD 卡
// GPIO39  — SD 卡
// GPIO40  — SD 卡
//
// 以及所有摄像头引脚（见第一节）

// ============================================================
// 四、允许但未分配 GPIO（可供扩展）
// ============================================================
//
// GPIO2, GPIO3, GPIO14, GPIO35, GPIO36, GPIO37,
// GPIO45, GPIO48

#endif // BOARD_PINS_H
