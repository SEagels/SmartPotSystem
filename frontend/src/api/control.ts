import client from './client';

export interface CommandResult {
  cmd_id: string;
  status: string;
  timestamp: string;
}

export interface CommandDetail {
  cmd_id: string;
  type: 'water' | 'photo' | 'config';
  status: string;
  request: Record<string, unknown>;
  response: Record<string, unknown> | null;
  created_at: string;
  completed_at: string | null;
}

export async function sendWaterCommand(deviceId: string, durationMs: number) {
  const res = await client.post(`/devices/${deviceId}/water`, { duration_ms: durationMs });
  return res.data.data as CommandResult;
}

export async function sendPhotoCommand(deviceId: string, burstCount: number = 3) {
  const res = await client.post(`/devices/${deviceId}/photo`, { burst_count: burstCount });
  return res.data.data as CommandResult;
}

export async function updateDeviceConfig(deviceId: string, config: Record<string, unknown>) {
  const res = await client.put(`/devices/${deviceId}/config`, config);
  return res.data.data;
}

export interface SyncResult {
  cmd: CommandResult;
  telemetry: Record<string, number> | null;
}

export async function sendSyncCommand(deviceId: string) {
  const res = await client.post(`/devices/${deviceId}/sync-sensors`);
  return res.data.data as SyncResult;
}

export async function getCommandStatus(deviceId: string, cmdId: string) {
  const res = await client.get(`/devices/${deviceId}/commands/${cmdId}`);
  return res.data.data as CommandDetail;
}
