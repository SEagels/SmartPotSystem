import { Card, Empty, Segmented } from 'antd';
import ReactECharts from 'echarts-for-react';
import { SENSOR_LABELS, SENSOR_UNITS } from '../utils/constants';
import type { HistoryDataPoint } from '../api/telemetry';

interface Props {
  data: HistoryDataPoint[];
  metric: string;
  onMetricChange: (m: string) => void;
  loading?: boolean;
}

const METRICS = ['temperature', 'humidity', 'soil_moisture', 'light_intensity'];

// ── 传感器历史趋势图表 ──
// 使用 ECharts 折线图展示近 24 小时的 avg/min/max 聚合数据
//   平均值线：实线 + 淡绿面积填充（主视觉焦点）
//   最小/最大值线：浅色虚线（辅助参考边界）
// Segmented 控件切换指标 → 触发 onMetricChange → 父组件重新 fetchChart 拉取数据
// X 轴：HH:MM 时间标签，数据点 >48 时旋转 45° 防止重叠
export default function SensorChart({ data, metric, onMetricChange, loading }: Props) {
  const unit = SENSOR_UNITS[metric] ?? '';

  const option = {
    tooltip: {
      trigger: 'axis' as const,
      formatter: (params: { name: string; value: number }[]) => {
        const p = params[0];
        return `${p.name}<br/>${SENSOR_LABELS[metric]}: ${p.value?.toFixed(1)} ${unit}`;
      },
    },
    legend: { data: ['平均值', '最小值', '最大值'], bottom: 0 },
    grid: { left: 8, right: 16, top: 8, bottom: 36 },
    xAxis: {
      type: 'category' as const,
      data: data.map((d) => d.timestamp.slice(11, 16)),
      axisLabel: { fontSize: 11, rotate: data.length > 48 ? 45 : 0 },
    },
    yAxis: {
      type: 'value' as const,
      axisLabel: { fontSize: 11, formatter: `{value} ${unit}` },
    },
    series: [
      {
        name: '平均值',
        type: 'line',
        data: data.map((d) => d.avg),
        smooth: true,
        symbol: 'none',
        lineStyle: { color: '#4caf50', width: 2 },
        areaStyle: { color: 'rgba(76,175,80,0.1)' },
      },
      {
        name: '最小值',
        type: 'line',
        data: data.map((d) => d.min),
        smooth: true,
        symbol: 'none',
        lineStyle: { color: '#91d5ff', width: 1, type: 'dashed' },
      },
      {
        name: '最大值',
        type: 'line',
        data: data.map((d) => d.max),
        smooth: true,
        symbol: 'none',
        lineStyle: { color: '#ffadd2', width: 1, type: 'dashed' },
      },
    ],
  };

  return (
    <Card
      title="历史趋势"
      size="small"
      bordered={false}
      style={{ borderRadius: 12 }}
      extra={
        <Segmented
          size="small"
          value={metric}
          onChange={(v) => onMetricChange(v as string)}
          options={METRICS.map((m) => ({ value: m, label: SENSOR_LABELS[m] }))}
        />
      }
    >
      {!loading && data.length === 0 ? (
        <Empty description="暂无历史数据" image={Empty.PRESENTED_IMAGE_SIMPLE} style={{ padding: '72px 0' }} />
      ) : (
        <ReactECharts option={option} style={{ height: 300 }} showLoading={loading} />
      )}
    </Card>
  );
}
