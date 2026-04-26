import { useState } from 'react';
import { Card, Slider, Button, Space, Typography, message } from 'antd';
import { sendWaterCommand } from '../api/control';

const { Text } = Typography;

interface Props {
  deviceId: string;
  disabled?: boolean;
}

export default function WateringControl({ deviceId, disabled }: Props) {
  const [duration, setDuration] = useState(5000);
  const [loading, setLoading] = useState(false);

  const handleWater = async () => {
    setLoading(true);
    try {
      await sendWaterCommand(deviceId, duration);
      message.success(`补水指令已发送 (${duration / 1000}秒)`);
    } catch {
      // error handled by interceptor
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card title="手动补水" size="small" bordered={false} style={{ borderRadius: 12 }}>
      <div style={{ marginBottom: 16 }}>
        <Text type="secondary">补水时长: {duration / 1000} 秒</Text>
        <Slider
          min={1000}
          max={30000}
          step={1000}
          value={duration}
          onChange={setDuration}
          marks={{ 1000: '1s', 10000: '10s', 20000: '20s', 30000: '30s' }}
          disabled={disabled}
        />
      </div>
      <Button
        type="primary"
        block
        loading={loading}
        disabled={disabled}
        onClick={handleWater}
        style={{ height: 44 }}
      >
        立即补水
      </Button>
    </Card>
  );
}
