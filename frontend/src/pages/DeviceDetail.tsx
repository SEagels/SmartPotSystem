import { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Row, Col, Card, Typography, Tabs, Spin, Button, message } from 'antd';
import { ArrowLeftOutlined, CameraOutlined } from '@ant-design/icons';
import { getDevice, type DeviceDetail as DeviceDetailType } from '../api/devices';
import { getLatestTelemetry, type LatestTelemetry } from '../api/telemetry';
import { sendPhotoCommand } from '../api/control';
import { useWebSocket } from '../hooks/useWebSocket';
import SensorCard from '../components/SensorCard';
import SensorChart from '../components/SensorChart';
import HealthGauge from '../components/HealthGauge';
import DeviceStatusDot from '../components/DeviceStatusDot';
import WateringControl from '../components/WateringControl';
import { getHistory, type HistoryDataPoint } from '../api/telemetry';

const { Title, Text } = Typography;

// ── 设备详情页 ──
// 核心数据流：
//   1. 初始化 → 并行请求设备信息 + 最新遥测（Promise.all）
//   2. 实时更新 → WebSocket telemetry_update 增量合并到当前遥测状态
//   3. 历史图表 → 切换指标时 fetchChart 拉取近 24 小时 15 分钟间隔聚合数据
// Tab 结构：概览 / 历史曲线 / 叶片图像 / 养护报告 / 设备设置
export default function DeviceDetail() {
  const { deviceId } = useParams<{ deviceId: string }>();
  const navigate = useNavigate();
  const [device, setDevice] = useState<DeviceDetailType | null>(null);
  const [telemetry, setTelemetry] = useState<LatestTelemetry | null>(null);
  const [loading, setLoading] = useState(true);
  const [photoLoading, setPhotoLoading] = useState(false);
  const [chartMetric, setChartMetric] = useState('temperature');
  const [chartData, setChartData] = useState<HistoryDataPoint[]>([]);
  const [chartLoading, setChartLoading] = useState(false);

  // 并行加载设备元信息 + 最新传感器数据，遥测失败不阻塞设备信息展示
  const fetchDevice = useCallback(async () => {
    if (!deviceId) return;
    try {
      const [dev, latest] = await Promise.all([
        getDevice(deviceId),
        getLatestTelemetry(deviceId).catch(() => null),
      ]);
      setDevice(dev);
      setTelemetry(latest);
    } catch {
      // 错误由 Axios 拦截器统一处理
    } finally {
      setLoading(false);
    }
  }, [deviceId]);

  // 拉取历史曲线数据：默认近 24 小时，15 分钟聚合粒度
  const fetchChart = useCallback(async (metric: string) => {
    if (!deviceId) return;
    setChartLoading(true);
    try {
      const data = await getHistory(deviceId, {
        metric,
        start: new Date(Date.now() - 86400000).toISOString(),
        end: new Date().toISOString(),
        interval: '15m',
      });
      setChartData(data.data_points);
    } catch {
      setChartData([]);
    } finally {
      setChartLoading(false);
    }
  }, [deviceId]);

  useEffect(() => {
    fetchDevice();
  }, [fetchDevice]);

  // 指标切换时重新拉取对应历史数据
  useEffect(() => {
    fetchChart(chartMetric);
  }, [chartMetric, fetchChart]);

  // WebSocket 实时更新：仅处理当前设备的事件，增量合并传感器数据
  useWebSocket(useCallback((event, wsDeviceId, payload) => {
    if (wsDeviceId !== deviceId) return; // 过滤其他设备的推送
    if (event === 'telemetry_update') {
      const p = payload as Record<string, number>;
      // 不可变更新：展开旧 sensors 再覆盖新值
      setTelemetry((prev) =>
        prev
          ? { ...prev, sensors: { ...prev.sensors, ...p }, timestamp: new Date().toISOString() }
          : prev,
      );
    }
  }, [deviceId]));

  // 发送拍照指令到后端，由后端通过 MQTT 下发给物理设备
  const handlePhoto = async () => {
    if (!deviceId) return;
    setPhotoLoading(true);
    try {
      await sendPhotoCommand(deviceId);
      message.success('拍照指令已发送');
    } catch {
      // handled
    } finally {
      setPhotoLoading(false);
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh' }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!device) return null;

  const tabItems = [
    {
      key: 'overview',
      label: '设备概览',
      children: (
        <div style={{ padding: '8px 0' }}>
          <div style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
            marginBottom: 20, padding: '0 4px',
          }}>
            <div>
              <Title level={4} style={{ margin: 0, fontFamily: 'var(--font-heading)', color: 'var(--color-primary-dark)' }}>
                {device.name}
              </Title>
              <Text type="secondary" style={{ fontSize: 13 }}>
                {device.plant_type_name || '未设置品种'} · {device.device_id}
              </Text>
            </div>
            <DeviceStatusDot online={device.online} />
          </div>

          <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
            <Col xs={12} sm={6}>
              <SensorCard metric="temperature" value={telemetry?.sensors.temperature} />
            </Col>
            <Col xs={12} sm={6}>
              <SensorCard metric="humidity" value={telemetry?.sensors.humidity} />
            </Col>
            <Col xs={12} sm={6}>
              <SensorCard metric="soil_moisture" value={telemetry?.sensors.soil_moisture} />
            </Col>
            <Col xs={12} sm={6}>
              <SensorCard metric="light_intensity" value={telemetry?.sensors.light_intensity} />
            </Col>
          </Row>

          <Row gutter={[16, 16]}>
            <Col xs={24} sm={12} md={8}>
              <Card bordered={false} style={{ borderRadius: 16, display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 200 }}>
                <HealthGauge score={85} size={140} />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={8}>
              <WateringControl deviceId={deviceId!} disabled={!device.online} />
            </Col>
            <Col xs={24} sm={12} md={8}>
              <Card
                title={<Text strong style={{ fontSize: 14 }}>远程拍照</Text>}
                size="small"
                bordered={false}
                style={{ borderRadius: 16 }}
              >
                <Text type="secondary" style={{ display: 'block', marginBottom: 12, fontSize: 12 }}>
                  触发设备立即拍摄叶片照片并进行病害检测
                </Text>
                <Button
                  icon={<CameraOutlined />}
                  block
                  loading={photoLoading}
                  disabled={!device.online}
                  onClick={handlePhoto}
                  style={{ height: 44, borderRadius: 10 }}
                >
                  立即拍照
                </Button>
              </Card>
            </Col>
          </Row>

          {telemetry && (
            <Row gutter={[12, 12]} style={{ marginTop: 20 }}>
              <Col xs={12} sm={6}>
                <Card size="small" bordered={false} style={{ borderRadius: 12, textAlign: 'center' }}>
                  <Text type="secondary" style={{ fontSize: 11 }}>水箱余量</Text>
                  <div className="sensor-value" style={{ fontSize: 18, color: '#06B6D4' }}>
                    {telemetry.actuators.water_tank_level_pct.toFixed(0)}%
                  </div>
                </Card>
              </Col>
              <Col xs={12} sm={6}>
                <Card size="small" bordered={false} style={{ borderRadius: 12, textAlign: 'center' }}>
                  <Text type="secondary" style={{ fontSize: 11 }}>水泵状态</Text>
                  <div style={{ fontSize: 18, marginTop: 2, color: telemetry.actuators.pump_running ? '#F97316' : '#94A3B8', fontWeight: 600 }}>
                    {telemetry.actuators.pump_running ? '运行中' : '停止'}
                  </div>
                </Card>
              </Col>
              <Col xs={12} sm={6}>
                <Card size="small" bordered={false} style={{ borderRadius: 12, textAlign: 'center' }}>
                  <Text type="secondary" style={{ fontSize: 11 }}>WiFi信号</Text>
                  <div className="sensor-value" style={{ fontSize: 18 }}>
                    {telemetry.system.wifi_rssi} dBm
                  </div>
                </Card>
              </Col>
              <Col xs={12} sm={6}>
                <Card size="small" bordered={false} style={{ borderRadius: 12, textAlign: 'center' }}>
                  <Text type="secondary" style={{ fontSize: 11 }}>运行时长</Text>
                  <div className="sensor-value" style={{ fontSize: 18 }}>
                    {Math.floor(telemetry.system.uptime_s / 3600)}h
                  </div>
                </Card>
              </Col>
            </Row>
          )}
        </div>
      ),
    },
    {
      key: 'charts',
      label: '历史曲线',
      children: (
        <div style={{ padding: '8px 0' }}>
          <SensorChart data={chartData} metric={chartMetric} onMetricChange={setChartMetric} loading={chartLoading} />
        </div>
      ),
    },
    {
      key: 'images',
      label: '叶片图像',
      children: (
        <div style={{ padding: 24, textAlign: 'center' }}>
          <Button type="primary" onClick={() => navigate(`/devices/${deviceId}/images`)} style={{ borderRadius: 10 }}>查看全部图像</Button>
        </div>
      ),
    },
    {
      key: 'reports',
      label: '养护报告',
      children: (
        <div style={{ padding: 24, textAlign: 'center' }}>
          <Button type="primary" onClick={() => navigate(`/devices/${deviceId}/reports`)} style={{ borderRadius: 10 }}>查看养护报告</Button>
        </div>
      ),
    },
    {
      key: 'settings',
      label: '设备设置',
      children: (
        <div style={{ padding: 24, textAlign: 'center' }}>
          <Button type="primary" onClick={() => navigate(`/devices/${deviceId}/settings`)} style={{ borderRadius: 10 }}>设备设置</Button>
        </div>
      ),
    },
  ];

  return (
    <div className="page-container">
      <Button
        type="link"
        onClick={() => navigate('/')}
        icon={<ArrowLeftOutlined />}
        style={{ padding: 0, marginBottom: 12, color: 'var(--color-primary)' }}
      >
        返回设备列表
      </Button>
      <Card bordered={false} style={{ borderRadius: 20, boxShadow: 'var(--shadow-card)' }}>
        <Tabs items={tabItems} />
      </Card>
    </div>
  );
}
