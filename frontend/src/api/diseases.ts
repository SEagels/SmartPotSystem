import client from './client';
import type { BBox } from './images';

export interface DiseaseRecord {
  detection_id: string;
  image_id: string;
  timestamp: string;
  disease_class: string;
  disease_name: string;
  confidence: number;
  severity: string;
  bbox: BBox;
  image_url: string;
}

export async function getDiseaseHistory(
  deviceId: string,
  params: { start?: string; end?: string },
) {
  const res = await client.get(`/devices/${deviceId}/diseases`, { params });
  return Array.isArray(res.data.data) ? (res.data.data as DiseaseRecord[]) : [];
}
