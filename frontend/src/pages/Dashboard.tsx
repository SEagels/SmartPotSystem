import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Row, Col, Card, Typography, Spin, Empty, Button, Tag, Modal, Form, Input, message } from 'antd';
import { PlusOutlined, AlertOutlined } from '@ant-design/icons';
import { getDevices, bindDevice, type DeviceListItem } from '../api/devices';
import { useWebSocket } from '../hooks/useWebSocket';
import DeviceStatusDot from '../components/DeviceStatusDot';

const { Title, Text } = Typography;

// 设备卡片封面图：根据在线/离线状态切换配色（绿色/灰色）
// 内联 SVG 绘制盆栽植物插图，离线时色值降为灰阶传达设备不可用
function PlantCover({ online }: { online: boolean }) {
  const gradient = online
    ? ['#ECFDF5', '#D1FAE5', '#A7F3D0']
    : ['#F8FAFC', '#F1F5F9', '#E2E8F0'];

  return (
    <div
      style={{
        height: 120,
        background: `linear-gradient(135deg, ${gradient[0]} 0%, ${gradient[1]} 50%, ${gradient[2]} 100%)`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      <svg width="64" height="64" viewBox="0 0 64 64" fill="none">
        <path
          d="M18 52V38C18 32 21 26 27 23"
          stroke={online ? '#15803D' : '#94A3B8'}
          strokeWidth="3"
          strokeLinecap="round"
        />
        <path
          d="M27 23C30 17 36 12 44 12C45 15 47 20 45 26C38 26 34 24 27 23Z"
          fill={online ? '#A7F3D0' : '#E2E8F0'}
          stroke={online ? '#15803D' : '#94A3B8'}
          strokeWidth="2.5"
          strokeLinejoin="round"
        />
        <path
          d="M24 38C18 35 12 38 12 46C12 49 15 52 21 52"
          stroke={online ? '#059669' : '#94A3B8'}
          strokeWidth="3"
          strokeLinecap="round"
        />
        <circle cx="18" cy="49" r="4" fill={online ? '#FBBF24' : '#CBD5E1'} />
        <circle cx="48" cy="16" r="2.5" fill={online ? '#D97706' : '#CBD5E1'} opacity="0.5" />
        <path
          d="M46 20C48 18 51 17 54 18"
          stroke={online ? '#22C55E' : '#CBD5E1'}
          strokeWidth="1.5"
          strokeLinecap="round"
          opacity="0.6"
        />
      </svg>
      <div
        style={{
          position: 'absolute',
          top: 8,
          right: 12,
          width: 8,
          height: 8,
          borderRadius: '50%',
          background: online ? '#16A34A' : '#CBD5E1',
        }}
      />
    </div>
  );
}

// ── 设备仪表板（首页）──
// 数据流：
//   初始加载 → getDevices() HTTP 请求获取设备列表
//   实时更新 → WebSocket 推送 telemetry_update / device_status 事件
//   不可变更新 → setDevices(prev => prev.map(...)) 仅替换匹配 deviceId 的项
// 交互：
//   点击设备卡片 → 导航到 /devices/:deviceId
//   绑定按钮 → 弹出 Modal 表单，后端校验设备编号 + 绑定码
export default function Dashboard() {
  const [devices, setDevices] = useState<DeviceListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [bindOpen, setBindOpen] = useState(false);
  const [bindLoading, setBindLoading] = useState(false);
  const [form] = Form.useForm();
  const navigate = useNavigate();

  const fetchDevices = useCallback(async () => {
    try {
      const data = await getDevices();
      setDevices(data);
    } catch {
      // 错误由 Axios 拦截器统一提示
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDevices();
  }, [fetchDevices]);

  // WebSocket 事件处理：不可变更新设备列表中的对应项
  // telemetry_update → 合并最新遥测数据到对应设备
  // device_status → 更新设备在线/离线状态
  useWebSocket(useCallback((event, deviceId, payload) => {
    if (event === 'telemetry_update') {
      // 不可变更新：展开旧对象 + 覆盖遥测字段，保留其他设备不变
      setDevices((prev) =>
        prev.map((d) =>
          d.device_id === deviceId
            ? {
                ...d,
                latest_telemetry: {
                  ...(payload as Record<string, number>),
                  temperature: (payload as Record<string, number>).temperature ?? d.latest_telemetry?.temperature,
                  humidity: (payload as Record<string, number>).humidity ?? d.latest_telemetry?.humidity,
                  soil_moisture: (payload as Record<string, number>).soil_moisture ?? d.latest_telemetry?.soil_moisture,
                  timestamp: new Date().toISOString(),
                } as DeviceListItem['latest_telemetry'],
              }
            : d,
        ),
      );
    }
    if (event === 'device_status') {
      setDevices((prev) =>
        prev.map((d) =>
          d.device_id === deviceId
            ? { ...d, online: (payload as { online: boolean }).online }
            : d,
        ),
      );
    }
  }, []));

  // 绑定设备：提交设备编号 + 绑定码 → 成功后刷新列表
  const handleBind = async (values: { device_id: string; bind_code: string }) => {
    setBindLoading(true);
    try {
      await bindDevice(values.device_id, values.bind_code);
      message.success('设备绑定成功');
      setBindOpen(false);
      form.resetFields();
      fetchDevices();
    } catch {
      // handled by interceptor
    } finally {
      setBindLoading(false);
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh' }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div className="page-container">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24 }}>
        <div>
          <Title level={4} style={{ margin: 0, fontFamily: 'var(--font-heading)', color: 'var(--color-primary-dark)' }}>
            我的设备
          </Title>
          <Text type="secondary" style={{ fontSize: 13 }}>
            点击设备卡片查看详情和控制
          </Text>
        </div>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => setBindOpen(true)}
          style={{ borderRadius: 20, height: 36 }}
        >
          绑定设备
        </Button>
      </div>

      {devices.length === 0 ? (
        <Card bordered={false} style={{ borderRadius: 16, textAlign: 'center', padding: '60px 0' }}>
          <Empty
            description="暂无设备"
            image={
              <svg width="80" height="80" viewBox="0 0 80 80" fill="none">
                <rect x="20" y="30" width="40" height="38" rx="6" stroke="#A7F3D0" strokeWidth="3" fill="#F0FDF4" />
                <path d="M28 20V30H52V20" stroke="#A7F3D0" strokeWidth="3" strokeLinecap="round" />
                <path d="M36 46L40 50L48 42" stroke="#22C55E" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M40 14V26" stroke="#D97706" strokeWidth="2" strokeLinecap="round" />
              </svg>
            }
          >
            <Text type="secondary">
              点击上方「绑定设备」按钮添加你的第一个智能花盆
            </Text>
          </Empty>
        </Card>
      ) : (
        <Row gutter={[16, 16]}>
          {devices.map((device) => (
            <Col xs={24} sm={12} lg={8} xl={6} key={device.device_id}>
              <Card
                className="dashboard-card"
                bordered={false}
                onClick={() => navigate(`/devices/${device.device_id}`)}
                cover={<PlantCover online={device.online} />}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <Text strong style={{ fontSize: 15, display: 'block' }}>{device.name}</Text>
                    <Text type="secondary" style={{ fontSize: 12 }}>{device.plant_type_name || '未设置品种'}</Text>
                  </div>
                  <DeviceStatusDot online={device.online} />
                </div>

                {device.has_active_alert && (
                  <Tag
                    color="error"
                    icon={<AlertOutlined />}
                    style={{ marginBottom: 10, borderRadius: 6, fontSize: 11 }}
                  >
                    有待处理告警
                  </Tag>
                )}

                {device.latest_telemetry ? (
                  <Row gutter={6} style={{ marginTop: 4 }}>
                    <Col span={8}>
                      <div className="stat-mini">
                        <Text style={{ fontSize: 15, fontWeight: 700, color: '#F97316', fontFamily: 'var(--font-heading)' }}>
                          {device.latest_telemetry.temperature.toFixed(1)}°
                        </Text>
                        <Text type="secondary" style={{ fontSize: 10 }}>温度</Text>
                      </div>
                    </Col>
                    <Col span={8}>
                      <div className="stat-mini">
                        <Text style={{ fontSize: 15, fontWeight: 700, color: '#3B82F6', fontFamily: 'var(--font-heading)' }}>
                          {device.latest_telemetry.humidity.toFixed(0)}%
                        </Text>
                        <Text type="secondary" style={{ fontSize: 10 }}>湿度</Text>
                      </div>
                    </Col>
                    <Col span={8}>
                      <div className="stat-mini">
                        <Text style={{ fontSize: 15, fontWeight: 700, color: '#8B5CF6', fontFamily: 'var(--font-heading)' }}>
                          {device.latest_telemetry.soil_moisture.toFixed(0)}%
                        </Text>
                        <Text type="secondary" style={{ fontSize: 10 }}>土壤</Text>
                      </div>
                    </Col>
                  </Row>
                ) : (
                  <Text type="secondary" style={{ fontSize: 12 }}>暂无传感器数据</Text>
                )}
              </Card>
            </Col>
          ))}
        </Row>
      )}

      <Modal
        title="绑定新设备"
        open={bindOpen}
        onCancel={() => { setBindOpen(false); form.resetFields(); }}
        footer={null}
        destroyOnClose
        width={420}
      >
        <div style={{ marginBottom: 20 }}>
          <Text type="secondary">
            请输入设备机身标签上的设备编号与绑定验证码。设备需先通电并连接 WiFi 后，才能完成绑定。
          </Text>
        </div>
        <Form form={form} layout="vertical" onFinish={handleBind}>
          <Form.Item
            name="device_id"
            label="设备编号"
            rules={[
              { required: true, message: '请输入设备编号' },
              { pattern: /^SP[A-Fa-f0-9]{6}$/, message: '设备编号格式：SP + 6位十六进制' },
            ]}
          >
            <Input placeholder="例如：SP1A2B3C" maxLength={16} style={{ borderRadius: 8 }} />
          </Form.Item>
          <Form.Item
            name="bind_code"
            label="绑定验证码"
            rules={[{ required: true, message: '请输入绑定验证码' }]}
          >
            <Input placeholder="设备机身标签上的8位验证码" maxLength={32} style={{ borderRadius: 8 }} />
          </Form.Item>
          <Form.Item style={{ marginBottom: 0 }}>
            <Button type="primary" htmlType="submit" block loading={bindLoading} style={{ borderRadius: 8, height: 40 }}>
              确认绑定
            </Button>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
