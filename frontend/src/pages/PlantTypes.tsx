import { useEffect, useState } from 'react';
import { Card, Typography, Spin, Empty, Row, Col, Modal, Descriptions, Tag, Button, Form, Input, Select, InputNumber, Divider, message } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { getPlants, createPlant, type PlantTypeItem, type CreatePlantData } from '../api/plants';

const { Title, Text } = Typography;

const CATEGORY_LABELS: Record<string, string> = {
  foliage: '观叶植物',
  succulent: '多肉植物',
  flowering: '观花植物',
  herb: '草本植物',
};

const CATEGORY_OPTIONS = [
  { value: 'foliage', label: '观叶植物' },
  { value: 'succulent', label: '多肉植物' },
  { value: 'flowering', label: '观花植物' },
  { value: 'herb', label: '草本植物' },
];

export default function PlantTypes() {
  const [plants, setPlants] = useState<PlantTypeItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<PlantTypeItem | null>(null);
  const [addOpen, setAddOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();

  const fetchPlants = () => {
    setLoading(true);
    getPlants()
      .then(setPlants)
      .catch(() => setPlants([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchPlants(); }, []);

  const handleAdd = async (values: CreatePlantData) => {
    setSaving(true);
    try {
      await createPlant(values);
      message.success('品种添加成功');
      setAddOpen(false);
      form.resetFields();
      fetchPlants();
    } catch {
      // handled by interceptor
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh' }}><Spin size="large" /></div>;
  }

  return (
    <div className="page-container">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <Title level={4} style={{ margin: 0 }}>植物品种</Title>
          <Text type="secondary">选择植物品种后，系统将自动配置最佳养护参数</Text>
        </div>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setAddOpen(true)} style={{ borderRadius: 10 }}>
          添加品种
        </Button>
      </div>

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

      <Modal
        title="添加植物品种"
        open={addOpen}
        onCancel={() => { setAddOpen(false); form.resetFields(); }}
        onOk={() => form.submit()}
        confirmLoading={saving}
        width={560}
      >
        <Form form={form} layout="vertical" onFinish={handleAdd} style={{ marginTop: 16 }}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="plant_type" label="品种代码" rules={[{ required: true, message: '请输入品种代码（英文）' }]}>
                <Input placeholder="例如: rose" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="name" label="品种名称" rules={[{ required: true }]}>
                <Input placeholder="例如: 玫瑰" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="category" label="类别" rules={[{ required: true }]}>
            <Select options={CATEGORY_OPTIONS} placeholder="选择植物类别" />
          </Form.Item>
          <Divider style={{ margin: '8px 0' }}>默认温度阈值</Divider>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name={['default_thresholds', 'temperature', 'min']} label="最低温度(°C)" initialValue={15}>
                <InputNumber style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name={['default_thresholds', 'temperature', 'max']} label="最高温度(°C)" initialValue={30}>
                <InputNumber style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Divider style={{ margin: '8px 0' }}>默认湿度阈值</Divider>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name={['default_thresholds', 'humidity', 'min']} label="最低湿度(%)" initialValue={30}>
                <InputNumber style={{ width: '100%' }} min={0} max={100} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name={['default_thresholds', 'humidity', 'max']} label="最高湿度(%)" initialValue={80}>
                <InputNumber style={{ width: '100%' }} min={0} max={100} />
              </Form.Item>
            </Col>
          </Row>
          <Divider style={{ margin: '8px 0' }}>默认土壤湿度阈值</Divider>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name={['default_thresholds', 'soil_moisture', 'min']} label="最低土壤湿度(%)" initialValue={20}>
                <InputNumber style={{ width: '100%' }} min={0} max={100} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name={['default_thresholds', 'soil_moisture', 'max']} label="最高土壤湿度(%)" initialValue={70}>
                <InputNumber style={{ width: '100%' }} min={0} max={100} />
              </Form.Item>
            </Col>
          </Row>
          <Divider style={{ margin: '8px 0' }}>补水配置</Divider>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name={['watering_cfg', 'trigger_soil_moisture']} label="补水触发土壤湿度(%)" initialValue={25}>
                <InputNumber style={{ width: '100%' }} min={0} max={100} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name={['watering_cfg', 'default_duration_ms']} label="默认补水时长(毫秒)" initialValue={5000}>
                <InputNumber style={{ width: '100%' }} min={1000} step={1000} />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>
    </div>
  );
}
