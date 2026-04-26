import client from './client';

export interface PlantTypeItem {
  plant_type: string;
  name: string;
  category: string;
  icon_url: string | null;
  default_thresholds: {
    temperature: { min: number; max: number };
    humidity: { min: number; max: number };
    soil_moisture: { min: number; max: number };
  };
  watering_cfg: {
    trigger_soil_moisture: number;
    default_duration_ms: number;
  };
}

export async function getPlants() {
  const res = await client.get('/plants');
  return res.data.data as PlantTypeItem[];
}

export async function getPlantType(plantType: string) {
  const res = await client.get(`/plants/${plantType}`);
  return res.data.data as PlantTypeItem;
}
