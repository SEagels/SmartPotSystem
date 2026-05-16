# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## Project Overview

SmartPot is an IoT smart flower pot system: ESP32-S3 hardware with sensors (DHT22, soil moisture, BH1750 light, OV2640 camera) communicates via MQTT to a FastAPI cloud backend. A React web dashboard provides device monitoring, disease detection viewing, and remote control. YOLOv11 ONNX model detects 12 plant disease classes. The system also supports auto-watering, timed photography, and LLM-based care recommendations.

## Common Commands

### Backend (`backend/`)

```bash
# Install (from backend/ directory)
pip install -e .
pip install amqtt          # embedded MQTT broker for dev mode (not in pyproject.toml)

# Dev server (SQLite, auto-creates tables + seeds demo data + embedded MQTT broker on :1883)
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Reset and re-seed demo data (idempotent, skips if data exists)
rm -f storage/smartpot.db && python -m seed_data.seed_demo

# Run tests
pytest

# Production mode (set ENVIRONMENT=production, requires PostgreSQL + TimescaleDB + Redis + MinIO + EMQX)
docker-compose up -d   # start infrastructure
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Frontend (`frontend/`)

```bash
npm install
npm run dev           # dev server on :5173, proxies /v1 to :8000
npm run build         # production build
npx tsc --noEmit      # type check only
```

### Firmware (`firmware/`)

```bash
# Install PlatformIO
pip install platformio

# Compile (fetches dependencies automatically)
cd firmware && pio run

# Compile + upload + serial monitor
pio run -t upload -t monitor

# Library dependencies (auto-managed by platformio.ini):
#   adafruit/DHT sensor library, claws/BH1750, knolleary/PubSubClient, bblanchon/ArduinoJson
```

Mock mode (`MOCK_MODE 1` in `include/config.h`) requires no hardware — sensors return simulated data and the camera returns a minimal valid JPEG. Set to `0` for real hardware.

Strict pin mapping is defined in `include/board_pins.h` (OV2640 camera, pump GPIO47, DHT11 GPIO21, BH1750 SDA=41/SCL=42, soil ADC GPIO1). Do not modify pin assignments.

### Model Training

```bash
# train.py at repo root — YOLOv11 training script
python train.py --data data.yaml --weights best.pt --epochs 100

# Dataset in data/ (YOLO format: images/ + labels/)
# Class mapping defined in data.yaml (12 plant disease classes in Chinese)
```

### Demo accounts (after seeding)

- `demo_user` / `123456` (4 devices)
- `test_gardener` / `123456` (1 device)

## Architecture

### Three-tier topology

```
ESP32 Hardware ──MQTT──> EMQX Broker ──> FastAPI Backend <──REST API── React Frontend
                     (paho-mqtt)        (MQTTManager)      (Axios /v1)    (Vite :5173)
```

- **Device ↔ Cloud**: MQTT topics under `smartpot/{device_id}/telemetry/...`, QoS 1, 5-min intervals. Images uploaded via HTTPS multipart (never through MQTT). Commands sent cloud→device with 30s ACK timeout.
- **Cloud ↔ App**: REST API at `/v1/*` with JWT Bearer auth. WebSocket at `/v1/ws?token=<jwt>` for real-time push (telemetry updates, alerts, command status, detection completion).
- **Dev mode**: SQLite via aiosqlite, local filesystem storage, embedded `amqtt` MQTT broker on :1883 (no external broker needed), demo data auto-seeded on startup.
- **Prod mode**: PostgreSQL + TimescaleDB (time-series), Redis (pub/sub), MinIO (S3-compatible image storage), EMQX broker.

### Backend layer structure (`backend/app/`)

```
api/          # Thin FastAPI route handlers — deserialize, call service, serialize
services/     # Business logic — device_service, telemetry_service, detection_service, etc.
models/       # SQLAlchemy ORM models (User, Device, Telemetry, Image, Detection, Alert, Command, WateringEvent, PlantType)
schemas/      # Pydantic request/response models
core/         # Infrastructure — database.py (async engine/session), mqtt.py, websocket_manager.py, security.py (JWT+bcrypt), redis.py
worker/       # Long-running async tasks — telemetry_consumer, image_processor, report_generator
```

Key patterns:
- **Dependency injection**: `get_db` yields an `AsyncSession` (auto-commit on success, rollback on exception). `get_current_user` decodes JWT and fetches User. `get_current_device` validates device ownership via composite key (device_id + user_id).
- **Service layer**: All business logic lives in `services/`. API routes are thin adapters.
- **API response envelope**: `{code: 0, message: "success", data: {...}}`. Non-zero codes for errors (1001=bad params, 1002=unauth, 2001=not found, etc.).
- **Storage abstraction**: `StorageBackend` base class with `LocalStorageBackend` and `MinIOStorageBackend` implementations, selected via `settings.STORAGE_BACKEND`.
- **MQTT topic routing**: Four wildcard topic handlers in `services/mqtt_service.py`:
  - `smartpot/+/telemetry` → `_handle_telemetry` — sensor data ingestion + WebSocket push
  - `smartpot/+/status` → `_handle_device_status` — device online state update + offline alerts
  - `smartpot/+/event/watering` → `_handle_watering_event` — watering event recording
  - `smartpot/+/response/+` → `_handle_command_response` — command ACK processing (30s timeout)
- **Dev MQTT broker**: `core/local_broker.py` runs an embedded `amqtt` MQTT 3.1.1 broker in-process. No external broker (EMQX/Mosquitto) needed in dev. Anonymous auth, max 50 connections.

### Frontend layer structure (`frontend/src/`)

```
api/          # Axios client + domain modules (auth, devices, telemetry, control, alerts, images, etc.)
pages/        # Route-level components — Dashboard, DeviceDetail, ImageGallery, Alerts, Reports, etc.
components/   # Reusable widgets — AppLayout, SensorCard, SensorChart, HealthGauge, WateringControl, BBoxOverlay
hooks/        # useAuth (context shortcut), useWebSocket (auto-reconnect)
contexts/     # AuthContext (JWT token + user state in localStorage)
```

Key patterns:
- **API client**: Axios instance at `/v1` with request interceptor (attach JWT) and response interceptor (check `code` field, handle 401/logout, parse 422 validation errors).
- **Auth flow**: `login()` stores token+user in localStorage and state. `ProtectedRoute` checks token existence.
- **WebSocket**: Single reusable hook with 5s auto-reconnect. Pages filter events by `deviceId`.
- **WebSocket event types**: `telemetry_update`, `device_status`, `watering_complete`, `command_update` — pushed per-user via `ws_manager.send_to_user()`.
- **Design system**: CSS custom properties in `styles/global.css` — "Organic Biophilic" theme with Plant Care palette (primary `#15803D`, bg `#F0FDF4`, accent `#D97706`), Lora+Raleway fonts, 4px spacing scale, green-tinted shadows.

### Disease detection pipeline

1. Image uploaded via REST → stored on disk/MinIO → DB record with status `pending_detection`
2. `image_processor` worker polls every 10s for pending images (batch of 5)
3. YOLOv11 ONNX model runs inference in thread pool (640×640 resize, NMS, class mapping to 12 Chinese disease names)
4. If model unavailable, falls back to rule-based detection (color histogram heuristics, low confidence 0.4–0.6)
5. Detections saved with bbox, confidence, severity (`mild`/`moderate`/`severe`), and treatment recommendation
6. Alerts generated for detections with confidence ≥ 0.7
7. Health score computed as `100 - (disease_count × 20 + max_confidence × 30)`, clamped to [10, 100]

### Database relationships

- `User` → has many `Device` (by `user_id` FK)
- `Device` → has many `Telemetry` (composite PK: time + device_id), `Image`, `Alert`, `Command`, `WateringEvent`
- `Image` → has many `Detection`
- `Device.plant_type` → FK to `PlantType.plant_type` (reference data)
- `Device.device_id` is a string (e.g., `SP000001`), not UUID

### Key config (`backend/app/config.py`)

`Settings` class loads from `.env`, provides `IS_DEV`/`IS_PROD`/`USE_SQLITE` convenience properties. Dev mode uses SQLite + local storage + auto-seeding. MQTT broker defaults to `localhost:1883`. JWT expiry defaults to 7 days.

### Important constraints

- `datetime.UTC` is not available on the `datetime.datetime` class in Python 3.14 — use `from datetime import UTC` and reference `UTC` directly, not `datetime.UTC`.
- SQLAlchemy `AsyncConnection` (from `engine.begin()`) does not support ORM `add_all()` — use `AsyncSession` from `get_sessionmaker()` for ORM operations.
- `core/database.py` exports `db_write_lock` (an `asyncio.Lock`) — all SQLite write operations MUST be wrapped with `async with db_write_lock:` to avoid concurrent write conflicts. Read-only operations can use `get_db_readonly()` which does not hold the lock.
- Frontend uses Ant Design 5 with extensive CSS variable overrides — avoid hardcoded colors in components, use `var(--color-*)` tokens.
- The `/ws` Vite proxy rule is defined but unused; `useWebSocket` connects directly to `hostname:8000/v1/ws`.
- `amqtt` is required for the embedded dev MQTT broker but is NOT listed in `pyproject.toml` — must be installed separately with `pip install amqtt`.

---

# AGENTS.md (中文版)

本文件为 Codex (Codex.ai/code) 在此仓库中工作时提供指导。

## 项目概述

SmartPot 是一套物联网智能花盆系统：ESP32-S3 硬件搭载传感器（DHT22温湿度、土壤湿度、BH1750光照、OV2640摄像头），通过 MQTT 与 FastAPI 云端后端通信。React Web 管理后台提供设备监控、病害检测查看和远程控制功能。YOLOv11 ONNX 模型可检测12种植物病害类别。系统还支持自动补水、定时拍照和基于大语言模型的养护建议。

## 常用命令

### 后端 (`backend/`)

```bash
# 安装依赖（在 backend/ 目录下执行）
pip install -e .
pip install amqtt          # 开发模式内嵌MQTT Broker（未包含在 pyproject.toml 中）

# 开发服务器（SQLite模式，自动建表 + 灌入演示数据 + 内嵌MQTT Broker监听 :1883）
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 重置并重新灌入演示数据（幂等操作，已有数据则跳过）
rm -f storage/smartpot.db && python -m seed_data.seed_demo

# 运行测试
pytest

# 生产模式（需设置 ENVIRONMENT=production，依赖 PostgreSQL + TimescaleDB + Redis + MinIO + EMQX）
docker-compose up -d   # 启动基础设施服务
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 前端 (`frontend/`)

```bash
npm install            # 安装依赖
npm run dev            # 开发服务器，端口 :5173，/v1 代理到 :8000
npm run build          # 生产构建
npx tsc --noEmit       # 仅类型检查
```

### 固件 (`firmware/`)

```bash
# 安装 PlatformIO
pip install platformio

# 编译（自动拉取依赖）
cd firmware && pio run

# 编译 + 烧录 + 串口监视
pio run -t upload -t monitor

# 库依赖（platformio.ini 自动管理）：
#   adafruit/DHT sensor library, claws/BH1750, knolleary/PubSubClient, bblanchon/ArduinoJson
```

Mock 模式 (`MOCK_MODE 1` in `include/config.h`) 无需硬件即可编译运行 —— 传感器返回模拟值，摄像头返回最小合法 JPEG。设置为 `0` 切换到真实硬件。

引脚映射严格定义在 `include/board_pins.h`（OV2640 摄像头、水泵 GPIO47、DHT11 GPIO21、BH1750 SDA=41/SCL=42、土壤 ADC GPIO1），不得修改。

### 模型训练

```bash
# train.py 位于仓库根目录 — YOLOv11 训练脚本
python train.py --data data.yaml --weights best.pt --epochs 100

# 数据集在 data/ (YOLO 格式: images/ + labels/)
# 类别映射定义在 data.yaml (12 种植物病害中文名)
```

### 演示账号（灌入数据后可用）

- `demo_user` / `123456`（4台设备）
- `test_gardener` / `123456`（1台设备）

## 架构设计

### 三层拓扑结构

```
ESP32 硬件 ──MQTT──> EMQX 消息中间件 ──> FastAPI 后端 <──REST API── React 前端
              (paho-mqtt)           (MQTTManager)      (Axios /v1)    (Vite :5173)
```

- **硬件 ↔ 云端**：MQTT 主题 `smartpot/{device_id}/telemetry/...`，QoS 1，每5分钟上报一次。图片通过 HTTPS multipart 上传（绝不通过 MQTT 传输二进制图片数据）。云端下发指令，设备30秒内回复 ACK。
- **云端 ↔ 应用**：REST API 路径 `/v1/*`，JWT Bearer 认证。WebSocket 路径 `/v1/ws?token=<jwt>` 用于实时推送（遥测更新、告警、指令状态、检测完成通知）。
- **开发模式**：SQLite + aiosqlite 异步驱动，本地文件系统存储，内嵌 `amqtt` MQTT Broker 监听 :1883（无需外部消息中间件），启动时自动灌入演示数据。
- **生产模式**：PostgreSQL + TimescaleDB（时序数据），Redis（发布/订阅），MinIO（S3兼容图片存储），EMQX 消息中间件。

### 后端分层结构 (`backend/app/`)

```
api/          # 薄 FastAPI 路由层 — 反序列化请求 → 调用业务层 → 序列化响应
services/     # 业务逻辑层 — device_service, telemetry_service, detection_service 等
models/       # SQLAlchemy ORM 模型 — User, Device, Telemetry, Image, Detection, Alert, Command, WateringEvent, PlantType
schemas/      # Pydantic 请求/响应模型，定义输入输出的数据形状
core/         # 基础设施层 — database.py(异步引擎/会话), mqtt.py, websocket_manager.py, security.py(JWT+bcrypt), redis.py
worker/       # 长时间运行的异步任务 — telemetry_consumer, image_processor, report_generator
```

关键设计模式：
- **依赖注入**：`get_db` 生成器提供 `AsyncSession`（成功自动提交，异常自动回滚）。`get_current_user` 解析 JWT 并查询用户。`get_current_device` 通过复合键（device_id + user_id）验证设备归属。
- **服务层封装**：所有业务逻辑集中在 `services/` 目录。API 路由只是薄适配层，不包含业务逻辑。
- **API 响应信封**：统一格式 `{code: 0, message: "success", data: {...}}`。非零 code 代表错误（1001=参数错误，1002=未认证，2001=设备不存在 等）。
- **存储抽象**：`StorageBackend` 抽象基类，有 `LocalStorageBackend` 和 `MinIOStorageBackend` 两种实现，通过 `settings.STORAGE_BACKEND` 切换。
- **MQTT 主题路由**：`services/mqtt_service.py` 中注册了四个通配符主题处理器：
  - `smartpot/+/telemetry` → `_handle_telemetry` — 传感器数据入库 + WebSocket 推送
  - `smartpot/+/status` → `_handle_device_status` — 设备在线状态更新 + 离线告警
  - `smartpot/+/event/watering` → `_handle_watering_event` — 浇水事件记录
  - `smartpot/+/response/+` → `_handle_command_response` — 指令 ACK 处理（30秒超时）
- **开发模式 MQTT Broker**：`core/local_broker.py` 在进程内运行基于 `amqtt` 的 MQTT 3.1.1 代理，无需安装 EMQX/Mosquitto。匿名认证，最大50连接。

### 前端分层结构 (`frontend/src/`)

```
api/          # Axios 客户端 + 按领域拆分的 API 模块（auth, devices, telemetry, control, alerts, images 等）
pages/        # 路由级页面组件 — Dashboard, DeviceDetail, ImageGallery, Alerts, Reports 等
components/   # 可复用组件 — AppLayout, SensorCard, SensorChart, HealthGauge, WateringControl, BBoxOverlay
hooks/        # useAuth（Context 快捷访问）, useWebSocket（自动重连）
contexts/     # AuthContext（JWT token + user 状态，持久化到 localStorage）
```

关键设计模式：
- **API 客户端**：Axios 实例基路径 `/v1`，请求拦截器注入 JWT，响应拦截器检查 `code` 字段、处理401跳转登录、解析422验证错误。
- **认证流程**：`login()` 将 token 和 user 信息同时存入 localStorage 和 React state。`ProtectedRoute` 组件检查 token 是否存在来决定是否放行。
- **WebSocket**：单个可复用 Hook，断线5秒自动重连。各页面通过 `deviceId` 过滤关注的事件。
- **WebSocket 事件类型**：`telemetry_update`、`device_status`、`watering_complete`、`command_update` — 通过 `ws_manager.send_to_user()` 按用户广播。
- **设计系统**：`styles/global.css` 中定义 CSS 自定义属性 — "有机仿生"主题，植物养护色板（主色 `#15803D`、背景 `#F0FDF4`、强调色 `#D97706`），Lora+Raleway 字体，4px 间距体系，带绿色调的柔和阴影。

### 病害检测流水线

1. 图片通过 REST API 上传 → 存储到本地磁盘/MinIO → 数据库记录状态为 `pending_detection`
2. `image_processor` 工作线程每10秒轮询待检测图片（每次取5张）
3. YOLOv11 ONNX 模型在线程池中异步推理（640×640 缩放、NMS 非极大值抑制、12类中文病害名称映射）
4. 如果模型不可用，回退到基于规则的检测（颜色直方图启发式算法，低置信度 0.4–0.6）
5. 检测结果保存：边界框坐标、置信度、严重程度（mild/moderate/severe）、防治建议文字
6. 置信度 ≥ 0.7 的检测结果自动生成告警
7. 健康评分 = `100 - (病害数量 × 20 + 最高置信度 × 30)`，范围限定在 [10, 100]

### 数据库关系

- `User` → 拥有多个 `Device`（通过 `user_id` 外键）
- `Device` → 拥有多个 `Telemetry`（复合主键：time + device_id）、`Image`、`Alert`、`Command`、`WateringEvent`
- `Image` → 拥有多个 `Detection`
- `Device.plant_type` → 外键引用 `PlantType.plant_type`（参考数据表）
- `Device.device_id` 是字符串类型（如 `SP000001`），不是 UUID

### 关键配置 (`backend/app/config.py`)

`Settings` 类从 `.env` 文件加载配置，提供 `IS_DEV`/`IS_PROD`/`USE_SQLITE` 便捷属性。开发模式使用 SQLite + 本地存储 + 内嵌 `amqtt` MQTT Broker + 自动播种演示数据。MQTT 代理默认地址 `localhost:1883`。JWT 默认有效期7天。

### 重要约束和踩坑记录

- **`datetime.UTC` 陷阱**：Python 3.14 中 `datetime.datetime` 类没有 `UTC` 属性。应使用 `from datetime import UTC` 直接引用 `UTC`，而非 `datetime.UTC`。
- **SQLAlchemy 会话选择**：`AsyncConnection`（通过 `engine.begin()` 获取）不支持 ORM 的 `add_all()` 方法。操作 ORM 对象必须使用 `get_sessionmaker()` 返回的 `AsyncSession`。
- **SQLite 写锁**：`core/database.py` 导出 `db_write_lock`（`asyncio.Lock`）— 所有 SQLite 写操作必须使用 `async with db_write_lock:` 包裹，避免并发写冲突。只读操作使用 `get_db_readonly()`，不持有锁。
- **前端颜色使用规范**：使用 Ant Design 5 组件时，避免在组件中硬编码颜色值，统一使用 `var(--color-*)` CSS 变量以保持主题一致性。
- **WebSocket 连接路径**：Vite 配置中的 `/ws` 代理规则实际未被使用；`useWebSocket` Hook 直接连接 `hostname:8000/v1/ws`，绕过了 Vite 代理。
- **`amqtt` 依赖**：开发模式内嵌 MQTT Broker 需要 `amqtt` 包，但未包含在 `pyproject.toml` 中，需单独 `pip install amqtt` 安装。
