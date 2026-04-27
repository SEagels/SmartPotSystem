import { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Typography, Spin, Empty, Descriptions, Tag, Row, Col, DatePicker, Segmented, Button, Space, Result, message } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import { getDailyReport, getWeeklyReport, generateReport, type DailyReport, type WeeklyReport } from '../api/reports';
import { formatDate, formatDateTime } from '../utils/format';
import HealthGauge from '../components/HealthGauge';
import dayjs from 'dayjs';

const { Title, Text, Paragraph } = Typography;

const SEVEN_DAYS_MS = 7 * 24 * 60 * 60 * 1000;

function getStorageKey(deviceId: string) {
  return `smartpot_reports_last_visit_${deviceId}`;
}

export default function Reports() {
  const { deviceId } = useParams<{ deviceId: string }>();
  const navigate = useNavigate();
  const [mode, setMode] = useState<'daily' | 'weekly'>('daily');
  const [date, setDate] = useState(formatDate(new Date().toISOString()));
  const [daily, setDaily] = useState<DailyReport | null>(null);
  const [weekly, setWeekly] = useState<WeeklyReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);

  // 七天清除：记录最新访问时间到 localStorage
  useEffect(() => {
    if (!deviceId) return;
    const key = getStorageKey(deviceId);
    const lastVisit = localStorage.getItem(key);
    const now = Date.now();
    if (lastVisit) {
      const elapsed = now - parseInt(lastVisit, 10);
      if (elapsed > SEVEN_DAYS_MS) {
        localStorage.removeItem(key);
      }
    }
    localStorage.setItem(key, String(now));
  }, [deviceId]);

  const fetchReport = useCallback(() => {
    if (!deviceId) return;
    setLoading(true);
    if (mode === 'daily') {
      getDailyReport(deviceId, date)
        .then(setDaily)
        .catch(() => setDaily(null))
        .finally(() => setLoading(false));
    } else {
      getWeeklyReport(deviceId, date)
        .then(setWeekly)
        .catch(() => setWeekly(null))
        .finally(() => setLoading(false));
    }
  }, [deviceId, mode, date]);

  useEffect(() => { fetchReport(); }, [fetchReport]);

  const handleGenerate = async () => {
    if (!deviceId) return;
    setGenerating(true);
    try {
      const data = await generateReport(deviceId, date);
      setDaily(data);
      message.success('养护报告已通过大模型生成');
    } catch {
      // handled
    } finally {
      setGenerating(false);
    }
  };

  if (loading) {
    return <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh' }}><Spin size="large" /></div>;
  }

  return (
    <div className="page-container">
      <Button type="link" onClick={() => navigate(`/devices/${deviceId}`)} style={{ padding: 0, marginBottom: 8 }}>
        ← 返回设备
      </Button>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>养护报告</Title>
        <Space>
          <DatePicker
            value={dayjs(date)}
            onChange={(d) => d && setDate(formatDate(d.toISOString()))}
          />
          <Segmented
            value={mode}
            onChange={(v) => setMode(v as 'daily' | 'weekly')}
            options={[
              { value: 'daily', label: '日报' },
              { value: 'weekly', label: '周报' },
            ]}
          />
        </Space>
      </div>

      {mode === 'daily' && daily ? (
        <Row gutter={[16, 16]}>
          <Col xs={24} md={8}>
            <Card bordered={false} style={{ borderRadius: 16, textAlign: 'center' }}>
              <Title level={5}>健康评分</Title>
              <div style={{ display: 'flex', justifyContent: 'center' }}>
                <HealthGauge score={daily.health_score ?? 0} size={140} />
              </div>
            </Card>
          </Col>
          <Col xs={24} md={16}>
            <Card bordered={false} style={{ borderRadius: 16 }} title="环境数据">
              <Row gutter={[16, 16]}>
                {(['temperature', 'humidity', 'soil_moisture'] as const).map((key) => {
                  const d = daily.environment_summary[key];
                  const hasData = d.avg != null;
                  return (
                    <Col span={8} key={key}>
                      <Card size="small" bordered style={{ textAlign: 'center', borderRadius: 8 }}>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {{ temperature: '温度', humidity: '湿度', soil_moisture: '土壤湿度' }[key]}
                        </Text>
                        <div style={{ fontSize: 22, fontWeight: 700, color: '#4caf50' }}>
                          {hasData ? `${d.avg!.toFixed(1)}{{ temperature: '°C', humidity: '%', soil_moisture: '%' }[key]}` : '--'}
                        </div>
                        <Text type="secondary" style={{ fontSize: 11 }}>
                          {hasData ? `${d.min!.toFixed(1)} ~ ${d.max!.toFixed(1)}` : '暂无数据'}
                        </Text>
                      </Card>
                    </Col>
                  );
                })}
              </Row>
            </Card>
          </Col>
          <Col xs={24}>
            <Card bordered={false} style={{ borderRadius: 16 }}>
              <Descriptions column={2} size="small" bordered>
                <Descriptions.Item label="补水次数">{daily.watering.count} 次</Descriptions.Item>
                <Descriptions.Item label="补水总量">{daily.watering.total_ml} ml</Descriptions.Item>
                <Descriptions.Item label="拍照张数">{daily.photos_taken}</Descriptions.Item>
                <Descriptions.Item label="病害告警">
                  <Tag color={daily.disease_alert ? 'red' : 'green'}>{daily.disease_alert ? '有' : '无'}</Tag>
                </Descriptions.Item>
              </Descriptions>
            </Card>
          </Col>
          {daily.suggestion && (
            <Col xs={24}>
              <Card bordered={false} style={{ borderRadius: 16, background: 'linear-gradient(135deg, #e8f5e9, #f1f8e9)' }}>
                <Title level={5}>AI 养护建议</Title>
                <Paragraph style={{ fontSize: 14 }}>{daily.suggestion}</Paragraph>
                {daily.suggestion_detail?.watering_recommendation && (
                  <Paragraph type="secondary" style={{ fontSize: 13, marginBottom: 0 }}>
                    {daily.suggestion_detail.watering_recommendation}
                  </Paragraph>
                )}
              </Card>
            </Col>
          )}
        </Row>
      ) : mode === 'weekly' && weekly ? (
        <Row gutter={[16, 16]}>
          <Col xs={24} md={8}>
            <Card bordered={false} style={{ borderRadius: 16, textAlign: 'center' }}>
              <Title level={5}>周均健康分</Title>
              <div style={{ display: 'flex', justifyContent: 'center' }}>
                <HealthGauge score={weekly.avg_health_score != null ? Math.round(weekly.avg_health_score) : 0} size={140} />
              </div>
              <Tag style={{ marginTop: 8 }} color={weekly.trend === 'improving' ? 'green' : weekly.trend === 'declining' ? 'red' : 'blue'}>
                {{ improving: '↗ 上升', stable: '→ 稳定', declining: '↘ 下降' }[weekly.trend] ?? weekly.trend}
              </Tag>
            </Card>
          </Col>
          <Col xs={24} md={16}>
            <Card bordered={false} style={{ borderRadius: 16 }} title="每日健康评分趋势">
              <ReactECharts
                style={{ height: 250 }}
                option={{
                  tooltip: { trigger: 'axis' },
                  xAxis: {
                    type: 'category',
                    data: weekly.daily_scores.map((_, i) => {
                      const d = dayjs(weekly.week_start).add(i, 'day');
                      return d.format('MM/DD');
                    }),
                  },
                  yAxis: { type: 'value', max: 100 },
                  series: [{
                    type: 'bar',
                    data: weekly.daily_scores,
                    itemStyle: {
                      color: {
                        type: 'linear',
                        x: 0, y: 0, x2: 0, y2: 1,
                        colorStops: [
                          { offset: 0, color: '#4caf50' },
                          { offset: 1, color: '#a5d6a7' },
                        ],
                      },
                      borderRadius: [8, 8, 0, 0],
                    },
                    barWidth: 24,
                  }],
                }}
              />
            </Card>
          </Col>
          <Col xs={24}>
            <Card bordered={false} style={{ borderRadius: 16 }}>
              <Descriptions column={2} size="small" bordered>
                <Descriptions.Item label="周补水次数">{weekly.total_watering_count} 次</Descriptions.Item>
                <Descriptions.Item label="周补水总量">{weekly.total_watering_ml} ml</Descriptions.Item>
                <Descriptions.Item label="病害告警数">{weekly.disease_alert_count}</Descriptions.Item>
                <Descriptions.Item label="环比健康分变化">
                  <Text style={{ color: (weekly.comparison_with_last_week.health_score_change ?? 0) >= 0 ? '#4caf50' : '#f5222d' }}>
                    {(weekly.comparison_with_last_week.health_score_change ?? 0) >= 0 ? '+' : ''}
                    {(weekly.comparison_with_last_week.health_score_change ?? 0).toFixed(1)}
                  </Text>
                </Descriptions.Item>
              </Descriptions>
            </Card>
          </Col>
          {weekly.suggestion && (
            <Col xs={24}>
              <Card bordered={false} style={{ borderRadius: 16, background: 'linear-gradient(135deg, #e8f5e9, #f1f8e9)' }}>
                <Title level={5}>AI 周养护建议</Title>
                <Paragraph style={{ fontSize: 14 }}>{weekly.suggestion}</Paragraph>
              </Card>
            </Col>
          )}
        </Row>
      ) : (
        <Card bordered={false} style={{ borderRadius: 16 }}>
          <Result
            icon={<ReloadOutlined />}
            title="暂无报告数据"
            subTitle="当前日期暂无养护数据，可手动调用大模型生成养护报告。若未配置 LLM_API_KEY，系统将使用内置规则生成建议。"
            extra={
              <Space>
                <Button onClick={fetchReport}>重新加载</Button>
                <Button type="primary" loading={generating} onClick={handleGenerate}>
                  生成养护报告
                </Button>
              </Space>
            }
          />
        </Card>
      )}
    </div>
  );
}
