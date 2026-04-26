import { useEffect, useState } from 'react';
import { Card, Typography, Spin, Empty, Row, Col, Modal, Descriptions, Tag } from 'antd';
import { getPlants, type PlantTypeItem } from '../api/plants';

const { Title, Text } = Typography;

const CATEGORY_LABELS: Record<string, string> = {
  foliage: '观叶植物',
  succulent: '多肉植物',
  flowering: '观花植物',
  herb: '草本植物',
};

export default function PlantTypes() {
  const [plants, setPlants] = useState<PlantTypeItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<PlantTypeItem | null>(null);

  useEffect(() => {
    getPlants()
      .then(setPlants)
      .catch(() => setPlants([]))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh' }}><Spin size="large" /></div>;
  }

  return (
    <div className="page-container">
      <Title level={4}>植物品种</Title>
      <Text type="secondary" style={{ display: 'block', marginBottom: 24 }}>
        选择植物品种后，系统将自动配置最佳养护参数
      </Text>

      {plants.length === 0 ? (
        <Empty description="暂无植物品种数据" />
      ) : (
        <Row gutter={[16, 16]}>
          {plants.map((plant) => (
            <Col xs={24} sm={12} md={8} lg={6} key={plant.plant_type}>
              <Card
                hoverable
                bordered={false}
                style={{ borderRadius: 16, textAlign: 'center' }}
                onClick={() => setSelected(plant)}
              >
                <svg width="48" height="48" viewBox="0 0 48 48" fill="none" style={{ margin: '0 auto 8px', display: 'block' }}>
                  <rect width="48" height="48" rx="14" fill="#F0FDF4" />
                  <path d="M12 38V28C12 22 15 18 20 15" stroke="#15803D" strokeWidth="2.5" strokeLinecap="round" />
                  <path d="M20 15C22 11 27 7 33 7C34 9 35 13 34 17C29 17 26 15 20 15Z" fill="#A7F3D0" stroke="#15803D" strokeWidth="2" strokeLinejoin="round" />
                  <circle cx="14" cy="35" r="2.5" fill="#FBBF24" />
                </svg>
                <Text strong style={{ fontSize: 16, display: 'block' }}>{plant.name}</Text>
                <Tag style={{ marginTop: 4 }}>{CATEGORY_LABELS[plant.category] ?? plant.category}</Tag>
              </Card>
            </Col>
          ))}
        </Row>
      )}

      <Modal
        title={selected?.name}
        open={!!selected}
        onCancel={() => setSelected(null)}
        footer={null}
        width={500}
      >
        {selected && (
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label="品种代码">{selected.plant_type}</Descriptions.Item>
            <Descriptions.Item label="类别">
              <Tag>{CATEGORY_LABELS[selected.category] ?? selected.category}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="适宜温度">
              {selected.default_thresholds.temperature.min}°C ~ {selected.default_thresholds.temperature.max}°C
            </Descriptions.Item>
            <Descriptions.Item label="适宜湿度">
              {selected.default_thresholds.humidity.min}% ~ {selected.default_thresholds.humidity.max}%
            </Descriptions.Item>
            <Descriptions.Item label="适宜土壤湿度">
              {selected.default_thresholds.soil_moisture.min}% ~ {selected.default_thresholds.soil_moisture.max}%
            </Descriptions.Item>
            <Descriptions.Item label="补水触发阈值">
              土壤湿度低于 {selected.watering_cfg.trigger_soil_moisture}%
            </Descriptions.Item>
            <Descriptions.Item label="默认补水时长">
              {(selected.watering_cfg.default_duration_ms / 1000).toFixed(0)} 秒
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </div>
  );
}
