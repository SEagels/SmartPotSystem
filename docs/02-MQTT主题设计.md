# 02 — MQTT 主题设计

## 1. 主题命名规范

```
smartpot/{device_id}/{category}/{subcategory}
```

- `device_id`：设备唯一标识，格式 `SP` + 6 位十六进制，如 `SP1A2B3C`
- 所有 Topic 使用 **小写字母 + 下划线**
- MQTT Broker：EMQX，TLS 加密，端口 8883

## 2. 主题层级总览

```
smartpot/{device_id}/
├── telemetry/              # 传感器遥测数据 (设备→云端)
├── image/
│   ├── uploaded            # 图片上传成功通知 (设备→云端)
│   └── result              # 图片检测结果摘要 (云端→设备)
├── event/
│   ├── watering            # 补水事件记录 (设备→云端)
│   └── alarm               # 本地告警 (设备→云端)
├── command/
│   ├── water               # 补水指令 (云端→设备)
│   ├── photo               # 立即拍照指令 (云端→设备)
│   └── config              # 配置更新指令 (云端→设备)
├── response/
│   ├── water               # 补水指令响应 (设备→云端)
│   ├── photo               # 拍照指令响应 (设备→云端)
│   └── config              # 配置指令响应 (设备→云端)
└── status/                 # 设备状态 (LWT: 上线/离线)
```

## 3. 各主题详细定义

### 3.1 遥测数据上报

**主题：** `smartpot/{device_id}/telemetry`

| 属性 | 值 |
|------|-----|
| 方向 | 设备 → 云端 |
| QoS | 1 |
| 频率 | 每 5 分钟 |
| 保留 | false |
| Payload | 见 [03-传感器数据格式.md](./03-传感器数据格式.md) |

### 3.2 图片上传通知

**主题：** `smartpot/{device_id}/image/uploaded`

| 属性 | 值 |
|------|-----|
| 方向 | 设备 → 云端 |
| QoS | 1 |
| 触发 | 图片 HTTPS 上传成功后 |
| 保留 | false |

**Payload：**
```json
{
  "image_id": "IMG-20260426-080001-SP1A2B3C",
  "timestamp": "2026-04-26T08:00:01Z",
  "url": "https://cdn.xxx.com/images/SP1A2B3C/2026/04/26/IMG-20260426-080001.jpg",
  "photo_index": 1
}
```

> 注：图片本身通过 HTTPS multipart/form-data 上传到 `POST /api/devices/{id}/images`，不在 MQTT 中传输二进制数据。

### 3.3 检测结果摘要

**主题：** `smartpot/{device_id}/image/result`

| 属性 | 值 |
|------|-----|
| 方向 | 云端 → 设备 |
| QoS | 1 |
| 触发 | YOLOv11 推理完成后 |
| 保留 | false |

**Payload：**
```json
{
  "image_id": "IMG-20260426-080001-SP1A2B3C",
  "timestamp": "2026-04-26T08:00:05Z",
  "detected": true,
  "disease_count": 2,
  "diseases": [
    {
      "class": "leaf_spot",
      "name_zh": "叶斑病",
      "confidence": 0.87,
      "bbox": {"x": 120, "y": 85, "w": 200, "h": 180}
    }
  ],
  "health_score": 72
}
```

### 3.4 补水事件记录

**主题：** `smartpot/{device_id}/event/watering`

| 属性 | 值 |
|------|-----|
| 方向 | 设备 → 云端 |
| QoS | 1 |
| 触发 | 每次补水结束后 |
| 保留 | false |

**Payload：**
```json
{
  "event_id": "EVT-WATER-20260426-080000-SP1A2B3C",
  "timestamp": "2026-04-26T08:00:00Z",
  "trigger": "auto",
  "duration_ms": 5000,
  "water_pumped_ml": 50,
  "reason": "soil_moisture_below_threshold",
  "soil_moisture_before": 22.5,
  "soil_moisture_after": 42.1
}
```

### 3.5 设备状态 (LWT)

**主题：** `smartpot/{device_id}/status`

| 属性 | 值 |
|------|-----|
| 方向 | 设备 → 云端 (自动) |
| QoS | 1 |
| 保留 | true |

**Last Will Testament：** 设备连接时自动发布 `{"online": true}` 的 retain 消息，断线时 Broker 自动发布 `{"online": false}`。

**Payload (上线)：**
```json
{
  "online": true,
  "timestamp": "2026-04-26T08:00:00Z",
  "firmware_version": "v1.2.3",
  "wifi_rssi": -45,
  "free_heap": 128000,
  "battery_voltage": 5.0
}
```

**Payload (离线 — 由 Broker 自动发布)：**
```json
{
  "online": false,
  "timestamp": "2026-04-26T15:30:00Z"
}
```

## 4. 控制指令

### 4.1 补水指令

**主题：** `smartpot/{device_id}/command/water`
**响应：** `smartpot/{device_id}/response/water`

| 方向 | QoS | 保留 |
|------|-----|------|
| 云端 → 设备 | 1 | false |

**指令 Payload：**
```json
{
  "cmd_id": "CMD-20260426-080000-WATER",
  "timestamp": "2026-04-26T08:00:00Z",
  "duration_ms": 5000,
  "source": "manual"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| duration_ms | int | 补水时长（毫秒），最大 30000 |
| source | string | `manual` 手动 / `auto` 自动 |

**响应 Payload：**
```json
{
  "cmd_id": "CMD-20260426-080000-WATER",
  "status": "executed",
  "timestamp": "2026-04-26T08:00:06Z",
  "actual_duration_ms": 5000,
  "water_pumped_ml": 50
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| status | string | `executed` 已执行 / `rejected` 拒绝 / `failed` 失败 |

### 4.2 拍照指令

**主题：** `smartpot/{device_id}/command/photo`
**响应：** `smartpot/{device_id}/response/photo`

**指令 Payload：**
```json
{
  "cmd_id": "CMD-20260426-080000-PHOTO",
  "timestamp": "2026-04-26T08:00:00Z",
  "burst_count": 3,
  "source": "manual"
}
```

**响应 Payload：**
```json
{
  "cmd_id": "CMD-20260426-080000-PHOTO",
  "status": "executed",
  "timestamp": "2026-04-26T08:00:03Z",
  "image_count": 3,
  "selected_index": 1
}
```

### 4.3 配置更新指令

**主题：** `smartpot/{device_id}/command/config`
**响应：** `smartpot/{device_id}/response/config`

**指令 Payload：**
```json
{
  "cmd_id": "CMD-20260426-080000-CONFIG",
  "timestamp": "2026-04-26T08:00:00Z",
  "changes": {
    "telemetry_interval_s": 300,
    "photo_schedule": ["08:00", "12:00", "16:00"],
    "soil_moisture_threshold": 30.0,
    "watering_max_duration_ms": 30000
  }
}
```

**响应 Payload：**
```json
{
  "cmd_id": "CMD-20260426-080000-CONFIG",
  "status": "applied",
  "timestamp": "2026-04-26T08:00:01Z"
}
```

## 5. QoS 策略

| 数据类型 | QoS | 理由 |
|---------|-----|------|
| telemetry | 1 | 允许偶尔丢失单条（5分钟后有新数据），但至少送达一次 |
| image/uploaded | 1 | 必须触发云端处理流水线 |
| image/result | 1 | 可丢失，设备不依赖此结果 |
| event/watering | 1 | 补水记录重要但允许重试 |
| command/* | 1 | 指令需送达，设备去重靠 cmd_id |
| response/* | 1 | 指令响应 |
| status (LWT) | 1 | 在线状态需保留 |
