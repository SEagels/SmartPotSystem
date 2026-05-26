// ── 全局常量与映射表 ──
// 设计意图：集中管理所有静态配置（端点、标签、单位、颜色），组件通过 metric 动态查表
// 避免在各处硬编码字符串和 if-else 颜色逻辑

// API 代理前缀：Vite devServer proxy 将 /v1 转发到后端 :8000，生产环境由 nginx 反代
export const API_BASE = '/v1';
export const WS_BASE = `ws://${window.location.hostname}:8000/v1/ws`;

// 病害英文名（模型输出）→ 中文展示名
export const DISEASE_NAME_MAP: Record<string, string> = {
  'ALS': 'ALS病害',
  'Angular Leafspot': '角斑病',
  'Anthracnose Fruit Rot': '炭疽病果腐',
  'Bean Rust': '豆锈病',
  'Blossom Blight': '花枯病',
  'Gray Mold': '灰霉病',
  'Leaf Spot': '叶斑病',
  'Powdery Mildew Fruit': '白粉病果',
  'Powdery Mildew Leaf': '白粉病叶',
  'disease': '病害',
  'leaf mold': '叶霉病',
  'spider mites': '红蜘蛛',
  suspected_abnormal: '疑似叶片异常',
};

// 传感器 metric key → 中文标签（SensorCard 标题 / SensorChart Segmented 选项）
export const SENSOR_LABELS: Record<string, string> = {
  temperature: '温度',
  humidity: '空气湿度',
  soil_moisture: '土壤湿度',
  light_intensity: '光照强度',
};

// 传感器 metric key → 物理单位（紧跟数值显示，如 "25.3°C"）
export const SENSOR_UNITS: Record<string, string> = {
  temperature: '°C',
  humidity: '%RH',
  soil_moisture: '%',
  light_intensity: 'lux',
};

// 告警类型 key → 中文名称（告警列表/详情页使用）
export const ALERT_TYPE_LABELS: Record<string, string> = {
  disease_detected: '病害检出',
  water_low: '水箱余量不足',
  device_offline: '设备离线',
  watering_failed: '补水失败',
  sensor_error: '传感器异常',
};

// 告警严重程度 → Tag 颜色（直接用于 Ant Design Tag color 属性）
export const SEVERITY_COLORS: Record<string, string> = {
  critical: '#f5222d',
  warning: '#fa8c16',
  info: '#1890ff',
};
