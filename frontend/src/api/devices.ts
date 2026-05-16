import client from './client';

export interface DeviceListItem {
  device_id: string;
  name: string;
  plant_type: string;
  plant_type_name: string;
  online: boolean;
  thumbnail_url?: string | null;
  latest_telemetry: {
    temperature: number;
    humidity: number;
    soil_moisture: number;
    timestamp: string;
  } | null;
  has_active_alert: boolean;
  bound_at: string;
}

export interface DeviceDetail {
  device_id: string;
  name: string;
  plant_type: string;
  plant_type_name: string;
  online: boolean;
  firmware_version: string;
  thumbnail_url?: string | null;
  bound_at: string;
  bind_code: string;
  latest_telemetry: Record<string, unknown> | null;
  thresholds: {
    temperature: { min: number; max: number };
    humidity: { min: number; max: number };
    soil_moisture: { min: number; max: number };
    light_intensity?: { min: number; max: number };
  } | null;
  photo_schedule: string[];
  today_summary: {
    watering_count: number;
    watering_total_ml: number;
    photo_count: number;
    disease_alerts: number;
  } | null;
}

export interface LanDeviceCandidate {
  device_id: string;
  ip: string;
  firmware_version?: string | null;
  wifi_rssi?: number | null;
  uptime_s?: number | null;
  mock_mode?: boolean | null;
  pump_running?: boolean | null;
}

export async function getDevices() {
  const res = await client.get('/devices');
  return res.data.data as DeviceListItem[];
}

export async function getDevice(deviceId: string) {
  const res = await client.get(`/devices/${deviceId}`);
  return res.data.data as DeviceDetail;
}

export async function bindDevice(deviceId: string, bindCode: string) {
  const res = await client.post('/devices/bind', { device_id: deviceId, bind_code: bindCode });
  return res.data.data;
}

export async function discoverLanDevices(cidr?: string) {
  const res = await client.get('/devices/lan-discover', { params: cidr ? { cidr } : undefined });
  return Array.isArray(res.data.data) ? (res.data.data as LanDeviceCandidate[]) : [];
}

export async function bindLanDevice(deviceId: string, ip: string, name?: string) {
  const res = await client.post('/devices/lan-bind', { device_id: deviceId, ip, name });
  return res.data.data;
}

export async function updateDevice(deviceId: string, data: { name?: string; plant_type?: string }) {
  const res = await client.put(`/devices/${deviceId}`, data);
  return res.data.data;
}

export async function unbindDevice(deviceId: string) {
  const res = await client.delete(`/devices/${deviceId}`);
  return res.data.data;
}
