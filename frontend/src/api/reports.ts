import client from './client';

export interface DailyReport {
  date: string;
  environment_summary: {
    temperature: { avg: number; min: number; max: number };
    humidity: { avg: number; min: number; max: number };
    soil_moisture: { avg: number; min: number; max: number };
  };
  watering: { count: number; total_ml: number; trigger_reasons: string[] };
  photos_taken: number;
  disease_alert: boolean;
  health_score: number;
  suggestion: string;
  suggestion_detail: {
    watering_recommendation: string;
    next_watering_time: string;
    attention_items: string[];
  };
}

export interface WeeklyReport {
  week_start: string;
  week_end: string;
  daily_scores: number[];
  avg_health_score: number;
  trend: string;
  total_watering_count: number;
  total_watering_ml: number;
  disease_alert_count: number;
  comparison_with_last_week: {
    health_score_change: number;
    watering_change_ml: number;
  };
  suggestion: string;
}

export async function getDailyReport(deviceId: string, date: string) {
  const res = await client.get(`/devices/${deviceId}/reports/daily`, { params: { date } });
  return res.data.data as DailyReport;
}

export async function getWeeklyReport(deviceId: string, date: string) {
  const res = await client.get(`/devices/${deviceId}/reports/weekly`, { params: { date } });
  return res.data.data as WeeklyReport;
}

export async function generateReport(deviceId: string, date?: string) {
  const res = await client.post(`/devices/${deviceId}/reports/generate`, null, { params: date ? { date } : {} });
  return res.data.data as DailyReport;
}
