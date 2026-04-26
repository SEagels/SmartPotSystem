import client from './client';

export interface AlertItem {
  alert_id: string;
  type: 'disease_detected' | 'water_low' | 'device_offline' | 'watering_failed' | 'sensor_error';
  severity: 'critical' | 'warning' | 'info';
  title: string;
  message: string;
  image_id: string | null;
  read: boolean;
  created_at: string;
}

export async function getAlerts(
  deviceId: string,
  params: { status?: 'unread' | 'read'; page?: number; page_size?: number },
) {
  const res = await client.get(`/devices/${deviceId}/alerts`, { params });
  return { data: res.data.data as AlertItem[], meta: res.data.meta };
}

export async function markAlertRead(alertId: string) {
  const res = await client.put(`/alerts/${alertId}/read`);
  return res.data.data;
}

export async function markAllAlertsRead(deviceId: string) {
  const res = await client.put(`/devices/${deviceId}/alerts/read-all`);
  return res.data.data;
}
