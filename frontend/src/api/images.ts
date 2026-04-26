import client from './client';

export interface ImageItem {
  image_id: string;
  url: string;
  annotated_url: string | null;
  timestamp: string;
  photo_index: number;
  detection_status: 'pending_detection' | 'processing' | 'completed' | 'failed';
  disease_count: number;
  health_score: number | null;
}

export interface BBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface DetectedDisease {
  class: string;
  name_zh: string;
  confidence: number;
  bbox: BBox;
  severity: string;
  recommendation: string;
}

export interface ImageDetail {
  image_id: string;
  url: string;
  annotated_url: string | null;
  timestamp: string;
  photo_index: number;
  quality_score: number;
  detection: {
    status: string;
    completed_at: string;
    diseases: DetectedDisease[];
    health_score: number;
  } | null;
}

export async function getImages(deviceId: string, date?: string) {
  const res = await client.get(`/devices/${deviceId}/images`, { params: date ? { date } : {} });
  return res.data.data as ImageItem[];
}

export async function getImageDetail(deviceId: string, imageId: string) {
  const res = await client.get(`/devices/${deviceId}/images/${imageId}`);
  return res.data.data as ImageDetail;
}

export async function uploadImage(deviceId: string, formData: FormData) {
  const res = await client.post(`/devices/${deviceId}/images`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data.data;
}
