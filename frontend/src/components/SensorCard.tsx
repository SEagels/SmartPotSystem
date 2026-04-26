import { Card, Typography } from 'antd';
import { SENSOR_LABELS, SENSOR_UNITS } from '../utils/constants';

const { Text } = Typography;

interface Props {
  metric: string;
  value: number | undefined | null;
  size?: 'default' | 'small';
}

// ── 传感器指标卡片 ──
// 可复用数值展示组件，通过 metric 查表获取中文标签和单位
// 颜色语义映射（传达"正常/预警/异常"状态直觉）：
//   温度 >30°C 红色（过热预警），<15°C 蓝色（低温），正常绿
//   土壤湿度 <25% 橙色（干旱预警），正常绿
//   其他指标默认绿，无数据灰色
// 支持 default/small 两种尺寸，small 用于详情页底部状态小卡片布局
export default function SensorCard({ metric, value, size = 'default' }: Props) {
  const label = SENSOR_LABELS[metric] ?? metric;
  const unit = SENSOR_UNITS[metric] ?? '';
  const isSmall = size === 'small';

  // 动态数值颜色：根据指标类型 + 阈值判断，让用户一眼感知植物环境是否正常
  const color = value != null
    ? metric === 'temperature' ? (value > 30 ? '#f5222d' : value < 15 ? '#1890ff' : '#4caf50')
    : metric === 'soil_moisture' ? (value < 25 ? '#fa8c16' : '#4caf50')
    : '#4caf50'
    : '#bfbfbf';

  return (
    <Card
      size={isSmall ? 'small' : 'default'}
      bordered={false}
      style={{ textAlign: 'center', borderRadius: 12, height: '100%' }}
    >
      <Text type="secondary" style={{ fontSize: isSmall ? 11 : 12 }}>{label}</Text>
      <div style={{ marginTop: 4 }}>
        <span className="sensor-value" style={{ fontSize: isSmall ? 20 : 28, color }}>
          {value != null ? value.toFixed(1) : '--'}
        </span>
        {value != null && (
          <Text type="secondary" style={{ marginLeft: 2, fontSize: isSmall ? 11 : 14 }}>{unit}</Text>
        )}
      </div>
    </Card>
  );
}

export function SensorCardMini({ metric, value }: Props) {
  return <SensorCard metric={metric} value={value} size="small" />;
}
