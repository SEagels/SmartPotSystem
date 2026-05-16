import { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Row, Col, Card, Typography, Tabs, Spin, Button, message, Image, Tag, Empty, Form, Input, Select, Popconfirm, Divider, DatePicker, Segmented, Space } from 'antd';
import { ArrowLeftOutlined, CameraOutlined, PictureOutlined, FileTextOutlined, SyncOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import type { Dayjs } from 'dayjs';
import { getDevice, updateDevice, unbindDevice, type DeviceDetail as DeviceDetailType } from '../api/devices';
import { getLatestTelemetry, type LatestTelemetry } from '../api/telemetry';
import { sendPhotoCommand, sendSyncCommand } from '../api/control';
import { useWebSocket } from '../hooks/useWebSocket';
import SensorCard from '../components/SensorCard';
import SensorChart from '../components/SensorChart';
import HealthGauge from '../components/HealthGauge';
import DeviceStatusDot from '../components/DeviceStatusDot';
import WateringControl from '../components/WateringControl';
import { getHistory, type HistoryDataPoint } from '../api/telemetry';
import { getImages, type ImageItem } from '../api/images';
import { getDailyReport, type DailyReport } from '../api/reports';
import { getPlants, type PlantTypeItem } from '../api/plants';
import { formatDate, formatDateTime } from '../utils/format';

const { Title, Text, Paragraph } = Typography;

// 设备详情页 —— 一级页面概览集成传感器、图片预览、报告摘要、设备设置
export default function DeviceDetail() {
  const { deviceId } = useParams<{ deviceId: string }>();
  const navigate = useNavigate();
  const [device, setDevice] = useState<DeviceDetailType | null>(null);
  const [telemetry, setTelemetry] = useState<LatestTelemetry | null>(null);
  const [loading, setLoading] = useState(true);
  const [photoLoading, setPhotoLoading] = useState(false);
  const [syncLoading, setSyncLoading] = useState(false);
  const [chartMetric, setChartMetric] = useState('temperature');
  const [chartRange, setChartRange] = useState<'day' | 'week'>('day');
  const [chartDate, setChartDate] = useState<Dayjs>(dayjs());
  const [chartData, setChartData] = useState<HistoryDataPoint[]>([]);
  const [chartLoading, setChartLoading] = useState(false);

  const [recentImages, setRecentImages] = useState<ImageItem[]>([]);
  const [imagesLoading, setImagesLoading] = useState(false);

  const [latestReport, setLatestReport] = useState<DailyReport | null>(null);
  const [reportLoading, setReportLoading] = useState(false);

  const [plants, setPlants] = useState<PlantTypeItem[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [settingsForm] = Form.useForm();
  const [pumpRunning, setPumpRunning] = useState(false);

  const fetchDevice = useCallback(async () => {
    if (!deviceId) return;
    setError(null);
    try {
      const [dev, latest] = await Promise.all([
        getDevice(deviceId),
        getLatestTelemetry(deviceId).catch(() => null),
      ]);
      setDevice(dev);
      setTelemetry(latest);

      setImagesLoading(true);
      setReportLoading(true);
      getImages(deviceId)
        .then((imgs) => setRecentImages(imgs.slice(0, 3)))
        .catch(() => setRecentImages([]))
        .finally(() => setImagesLoading(false));
      getDailyReport(deviceId, formatDate(new Date().toISOString()))
        .then(setLatestReport)
        .catch(() => setLatestReport(null))
        .finally(() => setReportLoading(false));
      getPlants()
        .then(setPlants)
        .catch(() => setPlants([]));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '设备信息加载失败');
    } finally {
      setLoading(false);
    }
  }, [deviceId]);

  const fetchChart = useCallback(async (metric: string, range: 'day' | 'week', date: Dayjs) => {
    if (!deviceId) return;
    setChartLoading(true);
    try {
      const start = range === 'day'
        ? date.startOf('day')
        : date.startOf('day').subtract(6, 'day');
      const end = date.endOf('day');
      const data = await getHistory(deviceId, {
        metric,
        start: start.toISOString(),
        end: end.toISOString(),
        interval: range === 'day' ? '15m' : '1h',
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

  useEffect(() => {
    if (!deviceId) return;
    const timer = window.setInterval(async () => {
      try {
        const [dev, latest] = await Promise.all([
          getDevice(deviceId),
          getLatestTelemetry(deviceId).catch(() => null),
        ]);
        setDevice((prev) => prev ? { ...prev, online: dev.online, firmware_version: dev.firmware_version } : dev);
        setTelemetry(latest);
      } catch {
        // 在线状态轮询失败时保持当前页面，避免打断用户操作
      }
    }, 15000);
    return () => window.clearInterval(timer);
  }, [deviceId]);

  useEffect(() => {
    fetchChart(chartMetric, chartRange, chartDate);
  }, [chartMetric, chartRange, chartDate, fetchChart]);

  useEffect(() => {
    if (device) {
      settingsForm.setFieldsValue({
        name: device.name,
        plant_type: device.plant_type,
      });
    }
  }, [device, settingsForm]);

  useWebSocket(useCallback((event, wsDeviceId, payload) => {
    if (wsDeviceId !== deviceId) return;
    if (event === 'telemetry_update') {
      const p = payload as Record<string, number>;
      setTelemetry((prev) =>
        prev
          ? { ...prev, sensors: { ...prev.sensors, ...p }, timestamp: new Date().toISOString() }
          : prev,
      );
    }
  }, [deviceId]));

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

  const handleSync = async () => {
    if (!deviceId) return;
    setSyncLoading(true);
    try {
      const res = await sendSyncCommand(deviceId);
      if (res && (res as any).telemetry) {
        const sensors = (res as any).telemetry as Record<string, number>;
        setTelemetry((prev) =>
          prev
            ? { ...prev, sensors: { ...prev.sensors, ...sensors }, timestamp: new Date().toISOString() }
            : prev,
        );
        message.success('传感器数据已同步');
      } else {
        message.warning('指令已发送但设备未响应');
      }
    } catch {
      // handled
    } finally {
      setSyncLoading(false);
    }
  };

  const handleSaveSettings = async (values: { name: string; plant_type: string }) => {
    if (!deviceId) return;
    setSaving(true);
    try {
      await updateDevice(deviceId, values);
      message.success('设备信息已更新');
      setDevice((prev) => prev ? { ...prev, name: values.name, plant_type: values.plant_type } : prev);
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
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh' }}>
        <Spin size="large" />
      </div>
    );
  }

  if (error) {
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
        <Card bordered={false} style={{ borderRadius: 20, boxShadow: 'var(--shadow-card)', textAlign: 'center', padding: '60px 0' }}>
          <Empty description={error} image={Empty.PRESENTED_IMAGE_SIMPLE}>
            <Button type="primary" onClick={() => fetchDevice()}>重新加载</Button>
          </Empty>
        </Card>
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
                <HealthGauge score={latestReport?.health_score ?? 85} size={140} />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={8}>
              <WateringControl
                deviceId={deviceId!}
                disabled={!device.online}
                pumpRunning={pumpRunning}
                onPumpStart={() => setPumpRunning(true)}
                onPumpStop={() => setPumpRunning(false)}
              />
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
                <Button
                  icon={<SyncOutlined />}
                  block
                  loading={syncLoading}
                  disabled={!device.online}
                  onClick={handleSync}
                  style={{ height: 44, borderRadius: 10, marginTop: 8 }}
                >
                  同步传感器
                </Button>
              </Card>
            </Col>
          </Row>

          {telemetry && (
            <Row gutter={[12, 12]} style={{ marginTop: 20 }}>
              <Col xs={12} sm={8}>
                <Card size="small" bordered={false} style={{ borderRadius: 12, textAlign: 'center' }}>
                  <Text type="secondary" style={{ fontSize: 11 }}>水泵状态</Text>
                  <div style={{ fontSize: 18, marginTop: 2, color: pumpRunning ? '#F97316' : '#94A3B8', fontWeight: 600 }}>
                    {pumpRunning ? '运行中' : '停止'}
                  </div>
                </Card>
              </Col>
              <Col xs={12} sm={8}>
                <Card size="small" bordered={false} style={{ borderRadius: 12, textAlign: 'center' }}>
                  <Text type="secondary" style={{ fontSize: 11 }}>WiFi信号</Text>
                  <div className="sensor-value" style={{ fontSize: 18 }}>
                    {telemetry.system.wifi_rssi} dBm
                  </div>
                </Card>
              </Col>
              <Col xs={12} sm={8}>
                <Card size="small" bordered={false} style={{ borderRadius: 12, textAlign: 'center' }}>
                  <Text type="secondary" style={{ fontSize: 11 }}>运行时长</Text>
                  <div className="sensor-value" style={{ fontSize: 18 }}>
                    {Math.floor(telemetry.system.uptime_s / 3600)}h
                  </div>
                </Card>
              </Col>
            </Row>
          )}

          <Divider style={{ margin: '24px 0 16px' }} />

          {/* 叶片图像预览 */}
          <Card
            bordered={false}
            style={{ borderRadius: 16, marginBottom: 16 }}
            title={
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span><PictureOutlined style={{ marginRight: 8 }} />叶片图像</span>
                <Button type="link" size="small" onClick={() => navigate(`/devices/${deviceId}/images`)}>
                  查看全部 →
                </Button>
              </div>
            }
          >
            {imagesLoading ? (
              <Spin />
            ) : recentImages.length === 0 ? (
              <Empty description="暂无叶片图像" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            ) : (
              <Row gutter={[12, 12]}>
                {recentImages.map((img) => (
                  <Col xs={8} sm={6} md={4} key={img.image_id}>
                    <Card
                      hoverable
                      size="small"
                      bordered={false}
                      style={{ borderRadius: 10, overflow: 'hidden' }}
                      cover={
                        <div style={{ height: 120, overflow: 'hidden', background: '#f5f5f5' }}>
                          <Image
                            src={img.url}
                            alt="叶片"
                            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                            preview={{ mask: null }}
                            fallback="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgZmlsbD0iI2Y1ZjVmNSIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBkb21pbmFudC1iYXNlbGluZT0ibWlkZGxlIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmaWxsPSIjYmZiZmJmIiBmb250LXNpemU9IjE2Ij7mr4/mnK/lm77niYc8L3RleHQ+PC9zdmc+"
                          />
                        </div>
                      }
                      onClick={() => navigate(`/devices/${deviceId}/images/${img.image_id}`)}
                    >
                      <Text style={{ fontSize: 11 }} type="secondary">{formatDateTime(img.timestamp)}</Text>
                    </Card>
                  </Col>
                ))}
              </Row>
            )}
          </Card>

          {/* 最新养护报告摘要 */}
          <Card
            bordered={false}
            style={{ borderRadius: 16, marginBottom: 16 }}
            title={
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span><FileTextOutlined style={{ marginRight: 8 }} />最新养护报告</span>
                <Button type="link" size="small" onClick={() => navigate(`/devices/${deviceId}/reports`)}>
                  查看完整报告 →
                </Button>
              </div>
            }
          >
            {reportLoading ? (
              <Spin />
            ) : latestReport ? (
              <Row gutter={[16, 12]}>
                <Col xs={24} sm={8} style={{ textAlign: 'center' }}>
                  <Text type="secondary" style={{ fontSize: 12 }}>健康评分</Text>
                  <div style={{ fontSize: 32, fontWeight: 700, color: 'var(--color-primary)' }}>
                    {latestReport.health_score != null ? latestReport.health_score : '--'}
                  </div>
                </Col>
                <Col xs={24} sm={16}>
                  <Text type="secondary" style={{ fontSize: 12 }}>今日养护建议</Text>
                  <Paragraph style={{ margin: '4px 0 0', fontSize: 13, color: '#555' }} ellipsis={{ rows: 2 }}>
                    {latestReport.suggestion || '暂无建议'}
                  </Paragraph>
                  <div style={{ marginTop: 8, display: 'flex', gap: 12 }}>
                    <Text style={{ fontSize: 12 }} type="secondary">
                      补水 {latestReport.watering.count} 次
                    </Text>
                    <Text style={{ fontSize: 12 }} type="secondary">
                      拍照 {latestReport.photos_taken} 张
                    </Text>
                    {latestReport.disease_alert && (
                      <Tag color="red" style={{ margin: 0 }}>病害告警</Tag>
                    )}
                  </div>
                </Col>
              </Row>
            ) : (
              <Empty description="暂无报告数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
          </Card>

          {/* 设备设置内联 */}
          <Card
            bordered={false}
            style={{ borderRadius: 16 }}
            title="设备设置"
          >
            <Row gutter={[16, 16]}>
              <Col xs={24} md={12}>
                <Form form={settingsForm} layout="vertical" onFinish={handleSaveSettings}>
                  <Form.Item name="name" label="设备名称" rules={[{ required: true }]}>
                    <Input />
                  </Form.Item>
                  <Form.Item name="plant_type" label="植物品种">
                    <Select
                      showSearch
                      placeholder="选择植物品种（自动配置养护参数）"
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
              </Col>
              <Col xs={24} md={12}>
                <Card size="small" bordered style={{ borderRadius: 10, marginBottom: 12 }}>
                  <Text type="secondary" style={{ fontSize: 12 }}>设备 ID</Text>
                  <div style={{ fontFamily: 'monospace', fontSize: 14 }}>{device.device_id}</div>
                </Card>
                {device.thresholds && (
                  <Card size="small" bordered style={{ borderRadius: 10, marginBottom: 12 }}>
                    <Text type="secondary" style={{ fontSize: 12 }}>当前养护阈值</Text>
                    <div style={{ fontSize: 13, marginTop: 4 }}>
                      温度 {device.thresholds.temperature.min}°C ~ {device.thresholds.temperature.max}°C |&nbsp;
                      湿度 {device.thresholds.humidity.min}% ~ {device.thresholds.humidity.max}% |&nbsp;
                      土壤 {device.thresholds.soil_moisture.min}% ~ {device.thresholds.soil_moisture.max}%
                    </div>
                  </Card>
                )}
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
              </Col>
            </Row>
          </Card>
        </div>
      ),
    },
    {
      key: 'charts',
      label: '历史曲线',
      children: (
        <div style={{ padding: '8px 0' }}>
          <Card
            size="small"
            bordered={false}
            style={{ borderRadius: 12, marginBottom: 12 }}
          >
            <Space wrap size={12} style={{ width: '100%', justifyContent: 'space-between' }}>
              <Space wrap size={12}>
                <Segmented
                  size="small"
                  value={chartRange}
                  onChange={(value) => setChartRange(value as 'day' | 'week')}
                  options={[
                    { value: 'day', label: '单日曲线' },
                    { value: 'week', label: '一周曲线' },
                  ]}
                />
                <DatePicker
                  size="small"
                  allowClear={false}
                  value={chartDate}
                  onChange={(value) => value && setChartDate(value)}
                  disabledDate={(current) => Boolean(current && current > dayjs().endOf('day'))}
                />
              </Space>
              <Text type="secondary" style={{ fontSize: 12 }}>
                {chartRange === 'day'
                  ? `当前日期：${chartDate.format('YYYY-MM-DD')}`
                  : `当前范围：${chartDate.subtract(6, 'day').format('YYYY-MM-DD')} 至 ${chartDate.format('YYYY-MM-DD')}`}
              </Text>
            </Space>
          </Card>
          <SensorChart data={chartData} metric={chartMetric} onMetricChange={setChartMetric} loading={chartLoading} />
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
