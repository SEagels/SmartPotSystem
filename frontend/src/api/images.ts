import client from './client';

export interface ImageItem {
  image_id: string;
  url: string;
  enhanced_url?: string | null;
  detection_source?: 'original' | 'enhanced' | null;
  detection_image_url?: string | null;
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
  confidence_level?: 'high' | 'suspect' | 'healthy' | null;
  model_source?: 'yolo' | 'rule' | null;
  bbox: BBox;
  severity: string;
  recommendation: string;
}

export interface ImageDetail {
  image_id: string;
  url: string;
  enhanced_url?: string | null;
  detection_source?: 'original' | 'enhanced' | null;
  detection_image_url?: string | null;
  annotated_url: string | null;
  timestamp: string;
  photo_index: number;
  quality_score: number;
  light_condition?: string | null;
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

export async function deleteImage(deviceId: string, imageId: string) {
  const res = await client.delete(`/devices/${deviceId}/images/${imageId}`);
  return res.data;
}

export async function reDetectImages(deviceId: string) {
  const res = await client.post(`/devices/${deviceId}/images/re-detect`);
  return res.data as { code: number; message: string; data: { count: number } };
}

export async function uploadImage(deviceId: string, formData: FormData) {
  const res = await client.post(`/devices/${deviceId}/images`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data.data;
}
