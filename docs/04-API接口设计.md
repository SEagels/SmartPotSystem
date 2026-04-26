# 04 — API 接口设计

## 约定

- **Base URL：** `https://api.smartpot.example.com/v1`
- **认证：** Bearer Token (JWT)，Header `Authorization: Bearer <token>`
- **Content-Type：** `application/json`（文件上传除外）
- **时间戳：** 统一 ISO8601 UTC 格式 `2026-04-26T08:00:00Z`
- **分页：** `?page=1&page_size=20`，响应含 `meta` 分页信息

### 通用响应信封

```json
{
  "code": 0,
  "message": "success",
  "data": {},
  "meta": {
    "page": 1,
    "page_size": 20,
    "total": 128
  }
}
```

| code | 含义 |
|------|------|
| 0 | 成功 |
| 1001 | 参数错误 |
| 1002 | 未认证 / Token 过期 |
| 1003 | 无权限 |
| 2001 | 设备不存在 |
| 2002 | 设备离线 |
| 2003 | 指令超时 |
| 3001 | 资源不存在 |

---

## 1. 用户认证

### 1.1 注册

```
POST /auth/register
```

**Request：**
```json
{
  "username": "user123",
  "password": "Abc123456!",
  "phone": "13800138000"
}
```

**Response `data`：**
```json
{
  "user_id": "U-D3F5A2B1",
  "username": "user123",
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "expires_at": "2026-05-03T08:00:00Z"
}
```

### 1.2 登录

```
POST /auth/login
```

**Request：**
```json
{
  "username": "user123",
  "password": "Abc123456!"
}
```

**Response `data`：** 同注册

### 1.3 获取用户信息

```
GET /auth/profile
```

**Response `data`：**
```json
{
  "user_id": "U-D3F5A2B1",
  "username": "user123",
  "phone": "138****8000",
  "created_at": "2026-03-01T10:00:00Z",
  "device_count": 2
}
```

---

## 2. 设备管理

### 2.1 设备列表

```
GET /devices
```

**Response `data`：**
```json
[
  {
    "device_id": "SP1A2B3C",
    "name": "客厅龟背竹",
    "plant_type": "monstera_deliciosa",
    "plant_type_name": "龟背竹",
    "online": true,
    "latest_telemetry": {
      "temperature": 25.3,
      "humidity": 65.2,
      "soil_moisture": 42.8,
      "timestamp": "2026-04-26T08:00:00Z"
    },
    "has_active_alert": true,
    "bound_at": "2026-03-15T12:00:00Z"
  }
]
```

### 2.2 设备详情

```
GET /devices/{device_id}
```

**Response `data`：**
```json
{
  "device_id": "SP1A2B3C",
  "name": "客厅龟背竹",
  "plant_type": "monstera_deliciosa",
  "plant_type_name": "龟背竹",
  "online": true,
  "firmware_version": "v1.2.3",
  "latest_telemetry": { "..." : "..." },
  "thresholds": {
    "temperature": {"min": 15.0, "max": 32.0},
    "soil_moisture": {"min": 30.0, "max": 70.0}
  },
  "photo_schedule": ["08:00", "12:00", "16:00"],
  "today_summary": {
    "watering_count": 2,
    "watering_total_ml": 100,
    "photo_count": 2,
    "disease_alerts": 0
  }
}
```

### 2.3 绑定设备

```
POST /devices/bind
```

**Request：**
```json
{
  "device_id": "SP1A2B3C",
  "bind_code": "A1B2C3D4"
}
```

**Response `data`：**
```json
{
  "device_id": "SP1A2B3C",
  "name": "新设备-SP1A2B3C",
  "bound_at": "2026-04-26T08:00:00Z"
}
```

### 2.4 更新设备信息

```
PUT /devices/{device_id}
```

**Request：**
```json
{
  "name": "主卧绿萝",
  "plant_type": "epipremnum_aureum"
}
```

### 2.5 解绑设备

```
DELETE /devices/{device_id}
```

---

## 3. 遥测数据

### 3.1 最新传感器数据

```
GET /devices/{device_id}/telemetry/latest
```

**Response `data`：**
```json
{
  "device_id": "SP1A2B3C",
  "timestamp": "2026-04-26T08:00:00Z",
  "sensors": {
    "temperature": 25.3,
    "humidity": 65.2,
    "soil_moisture": 42.8,
    "light_intensity": 850.0
  },
  "actuators": {
    "pump_running": false,
    "water_tank_level_pct": 68.0
  },
  "system": {
    "wifi_rssi": -48,
    "uptime_s": 86400
  }
}
```

### 3.2 历史数据

```
GET /devices/{device_id}/telemetry/history?metric=temperature&start=2026-04-25T00:00:00Z&end=2026-04-26T00:00:00Z&interval=1h
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| metric | string | 是 | `temperature` / `humidity` / `soil_moisture` / `light_intensity` |
| start | string(ISO8601) | 是 | 起始时间 |
| end | string(ISO8601) | 是 | 结束时间 |
| interval | string | 否 | 聚合粒度：`5m` / `1h` / `6h` / `1d`，默认 `1h` |

**Response `data`：**
```json
{
  "metric": "temperature",
  "unit": "°C",
  "interval": "1h",
  "data_points": [
    {"timestamp": "2026-04-25T00:00:00Z", "avg": 24.5, "min": 24.1, "max": 24.9},
    {"timestamp": "2026-04-25T01:00:00Z", "avg": 24.3, "min": 24.0, "max": 24.6}
  ]
}
```

### 3.3 日统计摘要

```
GET /devices/{device_id}/telemetry/summary?date=2026-04-26
```

---

## 4. 图片与病害检测

### 4.1 上传图片

```
POST /devices/{device_id}/images
Content-Type: multipart/form-data
```

| 字段 | 类型 | 说明 |
|------|------|------|
| image | file | 图片文件 (jpg/png) |
| metadata | string(JSON) | 图片元数据 (见传感器数据格式 §4) |

**Response `data`：**
```json
{
  "image_id": "IMG-20260426-080001-SP1A2B3C",
  "url": "https://cdn.xxx.com/images/SP1A2B3C/2026/04/26/IMG-20260426-080001.jpg",
  "status": "pending_detection"
}
```

### 4.2 获取图片列表

```
GET /devices/{device_id}/images?date=2026-04-26
```

**Response `data`：**
```json
[
  {
    "image_id": "IMG-20260426-080001-SP1A2B3C",
    "url": "https://cdn.xxx.com/images/SP1A2B3C/.../IMG-xxx.jpg",
    "annotated_url": "https://cdn.xxx.com/images/SP1A2B3C/.../IMG-xxx-annotated.jpg",
    "timestamp": "2026-04-26T08:00:01Z",
    "photo_index": 1,
    "detection_status": "completed",
    "disease_count": 1,
    "health_score": 72
  }
]
```

### 4.3 获取单张图片及检测结果

```
GET /devices/{device_id}/images/{image_id}
```

**Response `data`：**
```json
{
  "image_id": "IMG-20260426-080001-SP1A2B3C",
  "url": "https://cdn.xxx.com/.../IMG-xxx.jpg",
  "annotated_url": "https://cdn.xxx.com/.../IMG-xxx-annotated.jpg",
  "timestamp": "2026-04-26T08:00:01Z",
  "photo_index": 1,
  "quality_score": 0.92,
  "detection": {
    "status": "completed",
    "completed_at": "2026-04-26T08:00:05Z",
    "diseases": [
      {
        "class": "leaf_spot",
        "name_zh": "叶斑病",
        "confidence": 0.87,
        "bbox": {"x": 120, "y": 85, "width": 200, "height": 180},
        "severity": "moderate",
        "recommendation": "建议喷洒多菌灵800倍液，间隔7天重复一次"
      }
    ],
    "health_score": 72
  }
}
```

| detection_status | 含义 |
|-----------------|------|
| `pending_detection` | 等待检测 |
| `processing` | 检测进行中 |
| `completed` | 检测完成 |
| `failed` | 检测失败 |

### 4.4 病害检测历史

```
GET /devices/{device_id}/diseases?start=2026-04-01&end=2026-04-26
```

**Response `data`：**
```json
[
  {
    "detection_id": "DET-20260426-0001",
    "image_id": "IMG-20260426-080001-SP1A2B3C",
    "timestamp": "2026-04-26T08:00:05Z",
    "disease_class": "leaf_spot",
    "disease_name": "叶斑病",
    "confidence": 0.87,
    "severity": "moderate",
    "bbox": {"x": 120, "y": 85, "width": 200, "height": 180},
    "image_url": "https://cdn.xxx.com/.../IMG-xxx-annotated.jpg"
  }
]
```

---

## 5. 告警

### 5.1 告警列表

```
GET /devices/{device_id}/alerts?status=unread&page=1&page_size=20
```

**Response `data`：**
```json
[
  {
    "alert_id": "ALT-20260426-0001",
    "type": "disease_detected",
    "severity": "warning",
    "title": "检测到叶斑病",
    "message": "您的龟背竹(客厅)在08:00的叶片图像中检测到叶斑病，置信度87%",
    "image_id": "IMG-20260426-080001-SP1A2B3C",
    "read": false,
    "created_at": "2026-04-26T08:00:06Z"
  },
  {
    "alert_id": "ALT-20260426-0002",
    "type": "water_low",
    "severity": "info",
    "title": "水箱余量不足",
    "message": "当前水箱余量仅15%，请及时加水",
    "read": true,
    "created_at": "2026-04-26T07:30:00Z"
  }
]
```

| alert type | 含义 |
|-----------|------|
| `disease_detected` | 病害检出 |
| `water_low` | 水箱余量低 |
| `device_offline` | 设备离线 |
| `watering_failed` | 补水失败 |
| `sensor_error` | 传感器异常 |

### 5.2 标记已读

```
PUT /alerts/{alert_id}/read
```

### 5.3 全部已读

```
PUT /devices/{device_id}/alerts/read-all
```

---

## 6. 远程控制

### 6.1 手动补水

```
POST /devices/{device_id}/water
```

**Request：**
```json
{
  "duration_ms": 5000
}
```

**Response `data`：**
```json
{
  "cmd_id": "CMD-20260426-080000-WATER",
  "status": "sent",
  "timestamp": "2026-04-26T08:00:00Z"
}
```

指令状态通过轮询或 WebSocket 推送返回最终结果。

### 6.2 立即拍照

```
POST /devices/{device_id}/photo
```

**Request：**
```json
{
  "burst_count": 3
}
```

**Response `data`：**
```json
{
  "cmd_id": "CMD-20260426-080000-PHOTO",
  "status": "sent",
  "timestamp": "2026-04-26T08:00:00Z"
}
```

### 6.3 更新设备配置

```
PUT /devices/{device_id}/config
```

**Request：**
```json
{
  "photo_schedule": ["07:00", "12:00", "18:00"],
  "telemetry_interval_s": 300,
  "watering_max_duration_ms": 30000
}
```

### 6.4 查询指令状态

```
GET /devices/{device_id}/commands/{cmd_id}
```

**Response `data`：**
```json
{
  "cmd_id": "CMD-20260426-080000-WATER",
  "type": "water",
  "status": "executed",
  "request": {"duration_ms": 5000},
  "response": {
    "actual_duration_ms": 5000,
    "water_pumped_ml": 50
  },
  "created_at": "2026-04-26T08:00:00Z",
  "completed_at": "2026-04-26T08:00:06Z"
}
```

---

## 7. 养护报告

### 7.1 日报

```
GET /devices/{device_id}/reports/daily?date=2026-04-26
```

**Response `data`：**
```json
{
  "date": "2026-04-26",
  "environment_summary": {
    "temperature": {"avg": 25.1, "min": 23.2, "max": 27.8},
    "humidity": {"avg": 62.5, "min": 55.0, "max": 70.1},
    "soil_moisture": {"avg": 40.2, "min": 22.5, "max": 48.0}
  },
  "watering": {
    "count": 2,
    "total_ml": 100,
    "trigger_reasons": ["auto_threshold", "manual"]
  },
  "photos_taken": 3,
  "disease_alert": false,
  "health_score": 88,
  "suggestion": "今日环境适宜，土壤湿度维持在正常范围，植株状态良好。明日建议继续保持当前养护节奏。",
  "suggestion_detail": {
    "watering_recommendation": "明日预计需补水1次，约50ml",
    "next_watering_time": "2026-04-27T08:00:00Z",
    "attention_items": []
  }
}
```

### 7.2 周报

```
GET /devices/{device_id}/reports/weekly?date=2026-04-26
```

**Response `data`：**
```json
{
  "week_start": "2026-04-20",
  "week_end": "2026-04-26",
  "daily_scores": [85, 90, 78, 82, 88, 91, 88],
  "avg_health_score": 86.0,
  "trend": "stable",
  "total_watering_count": 14,
  "total_watering_ml": 700,
  "disease_alert_count": 1,
  "comparison_with_last_week": {
    "health_score_change": 3.0,
    "watering_change_ml": -50
  },
  "suggestion": "本周植株整体状态稳定向好，土壤湿度控制有效。下周可适当减少单次补水量。"
}
```

---

## 8. 植物品种

### 8.1 品种列表

```
GET /plants
```

**Response `data`：**
```json
[
  {
    "plant_type": "monstera_deliciosa",
    "name": "龟背竹",
    "category": "foliage",
    "icon_url": "https://cdn.xxx.com/icons/monstera.png",
    "default_thresholds": {
      "temperature": {"min": 15.0, "max": 32.0},
      "humidity": {"min": 40.0, "max": 85.0},
      "soil_moisture": {"min": 30.0, "max": 70.0}
    },
    "watering_cfg": {
      "trigger_soil_moisture": 25.0,
      "default_duration_ms": 8000
    }
  }
]
```

### 8.2 品种详情

```
GET /plants/{plant_type}
```

---

## 9. WebSocket 实时推送

```
ws://api.smartpot.example.com/ws?token={jwt_token}
```

服务端推送事件类型：

| event | 说明 |
|-------|------|
| `telemetry_update` | 新遥测数据到达，直接推送 sensor 数据 |
| `alert_new` | 新告警产生 |
| `command_update` | 指令状态变更 |
| `detection_complete` | 图片检测完成 |
| `device_status` | 设备上线/离线 |

**示例推送：**
```json
{
  "event": "telemetry_update",
  "device_id": "SP1A2B3C",
  "timestamp": "2026-04-26T08:05:00Z",
  "payload": {
    "temperature": 25.4,
    "humidity": 65.0,
    "soil_moisture": 42.5,
    "light_intensity": 860.0
  }
}
```
