import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Typography, Spin, Form, Input, Select, Button, Descriptions, Tag, Popconfirm, message, Row, Col } from 'antd';
import { getDevice, updateDevice, unbindDevice, type DeviceDetail } from '../api/devices';
import { getPlants, type PlantTypeItem } from '../api/plants';
import { formatDateTime } from '../utils/format';

const { Title, Text } = Typography;

export default function DeviceSettings() {
  const { deviceId } = useParams<{ deviceId: string }>();
  const navigate = useNavigate();
  const [device, setDevice] = useState<DeviceDetail | null>(null);
  const [plants, setPlants] = useState<PlantTypeItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();

  useEffect(() => {
    if (!deviceId) return;
    Promise.all([
      getDevice(deviceId),
      getPlants().catch(() => []),
    ])
      .then(([dev, pl]) => {
        setDevice(dev);
        setPlants(pl);
        form.setFieldsValue({ name: dev.name, plant_type: dev.plant_type });
      })
      .finally(() => setLoading(false));
  }, [deviceId, form]);

  const handleSave = async (values: { name: string; plant_type: string }) => {
    if (!deviceId) return;
    setSaving(true);
    try {
      await updateDevice(deviceId, values);
      message.success('设备信息已更新');
    } catch {
      // handled
    } finally {
      setSaving(false);
    }
  };

  const handleUnbind = async () => {
    if (!deviceId) return;
    try {
      await unbindDevice(deviceId);
      message.success('设备已解绑');
      navigate('/', { replace: true });
    } catch {
      // handled
    }
  };

  if (loading) {
    return <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh' }}><Spin size="large" /></div>;
  }

  if (!device) return null;

  return (
    <div className="page-container">
      <Button type="link" onClick={() => navigate(`/devices/${deviceId}`)} style={{ padding: 0, marginBottom: 16 }}>
        ← 返回设备
      </Button>

      <Row gutter={[16, 16]}>
        <Col xs={24} md={12}>
          <Card bordered={false} style={{ borderRadius: 16 }} title="设备信息编辑">
            <Form form={form} layout="vertical" onFinish={handleSave}>
              <Form.Item name="name" label="设备名称" rules={[{ required: true, message: '请输入设备名称' }]}>
                <Input placeholder="例如：客厅龟背竹" />
              </Form.Item>
              <Form.Item name="plant_type" label="植物品种">
                <Select
                  showSearch
                  placeholder="选择植物品种"
                  options={plants.map((p) => ({ value: p.plant_type, label: p.name }))}
                  filterOption={(input, option) =>
                    (option?.label as string)?.toLowerCase().includes(input.toLowerCase())
                  }
                />
              </Form.Item>
              <Form.Item>
                <Button type="primary" htmlType="submit" loading={saving}>
                  保存修改
                </Button>
              </Form.Item>
            </Form>
          </Card>
        </Col>

        <Col xs={24} md={12}>
          <Card bordered={false} style={{ borderRadius: 16 }} title="设备详情">
            <Descriptions column={1} size="small" bordered>
              <Descriptions.Item label="设备 ID">{device.device_id}</Descriptions.Item>
              <Descriptions.Item label="在线状态">
                <Tag color={device.online ? 'green' : 'red'}>{device.online ? '在线' : '离线'}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="固件版本">{device.firmware_version}</Descriptions.Item>
              <Descriptions.Item label="拍照计划">
                {device.photo_schedule?.join(', ') ?? '未设置'}
              </Descriptions.Item>
              <Descriptions.Item label="绑定时间">{formatDateTime(device.bound_at)}</Descriptions.Item>
            </Descriptions>
          </Card>

          {device.thresholds && (
            <Card bordered={false} style={{ borderRadius: 16, marginTop: 16 }} title="当前阈值">
              <Descriptions column={1} size="small" bordered>
                <Descriptions.Item label="温度">
                  {device.thresholds.temperature.min}°C ~ {device.thresholds.temperature.max}°C
                </Descriptions.Item>
                <Descriptions.Item label="湿度">
                  {device.thresholds.humidity.min}% ~ {device.thresholds.humidity.max}%
                </Descriptions.Item>
                <Descriptions.Item label="土壤湿度">
                  {device.thresholds.soil_moisture.min}% ~ {device.thresholds.soil_moisture.max}%
                </Descriptions.Item>
              </Descriptions>
            </Card>
          )}

          <Card bordered={false} style={{ borderRadius: 16, marginTop: 16 }}>
            <Popconfirm
              title="确认解绑设备？"
              description="解绑后设备数据将不再同步到您的账号"
              onConfirm={handleUnbind}
              okText="确认解绑"
              cancelText="取消"
              okButtonProps={{ danger: true }}
            >
              <Button danger block>解绑设备</Button>
            </Popconfirm>
          </Card>
        </Col>
      </Row>
    </div>
  );
}
