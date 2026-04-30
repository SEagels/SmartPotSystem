import client from './client';

export interface LatestTelemetry {
  device_id: string;
  timestamp: string;
  sensors: {
    temperature: number;
    humidity: number;
    soil_moisture: number;
    light_intensity: number;
  };
  actuators: {
    pump_running: boolean;
    led_on: boolean;
  };
  system: {
    wifi_rssi: number;
    uptime_s: number;
  };
}

export interface HistoryDataPoint {
  timestamp: string;
  avg: number;
  min: number;
  max: number;
}

export interface HistoryData {
  metric: string;
  unit: string;
  interval: string;
  data_points: HistoryDataPoint[];
}

export interface DailySummary {
  device_id: string;
  period: string;
  date: string;
  summary: {
    temperature: { avg: number; min: number; max: number };
    humidity: { avg: number; min: number; max: number };
    soil_moisture: { avg: number; min: number; max: number };
    light_intensity: { avg: number; min: number; max: number };
  };
  watering_count: number;
  watering_total_ml: number;
  photo_count: number;
  disease_alerts: number;
}

export async function getLatestTelemetry(deviceId: string) {
  const res = await client.get(`/devices/${deviceId}/telemetry/latest`);
  return res.data.data as LatestTelemetry;
}

export async function getHistory(
  deviceId: string,
  params: { metric: string; start: string; end: string; interval?: string },
) {
  const res = await client.get(`/devices/${deviceId}/telemetry/history`, { params });
  return res.data.data as HistoryData;
}

export async function getDailySummary(deviceId: string, date: string) {
  const res = await client.get(`/devices/${deviceId}/telemetry/summary`, { params: { date } });
  return res.data.data as DailySummary;
}
