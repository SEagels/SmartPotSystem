import { useState, useEffect, useRef } from 'react';
import { Card, Slider, Button, Tag, Typography, message } from 'antd';
import { sendWaterCommand } from '../api/control';

const { Text } = Typography;

interface Props {
  deviceId: string;
  disabled?: boolean;
  pumpRunning: boolean;
  onPumpStart: (durationMs: number) => void;
  onPumpStop: () => void;
}

export default function WateringControl({
  deviceId, disabled, pumpRunning, onPumpStart, onPumpStop,
}: Props) {
  const [duration, setDuration] = useState(5000);
  const [loading, setLoading] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  const handleWater = async () => {
    if (pumpRunning) return;
    setLoading(true);
    try {
      await sendWaterCommand(deviceId, duration);
      message.success(`补水指令已发送 (${duration / 1000}秒)`);
      onPumpStart(duration);
      if (timerRef.current) clearTimeout(timerRef.current);
      timerRef.current = setTimeout(() => {
        onPumpStop();
      }, duration);
    } catch {
      // error handled by interceptor
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card
      title={
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>手动补水</span>
          <Tag color={pumpRunning ? 'orange' : 'default'} style={{ margin: 0 }}>
            {pumpRunning ? '运行中' : '停止'}
          </Tag>
        </div>
      }
      size="small"
      bordered={false}
      style={{ borderRadius: 12 }}
    >
      <div style={{ marginBottom: 16 }}>
        <Text type="secondary">补水时长: {duration / 1000} 秒</Text>
        <Slider
          min={1000}
          max={30000}
          step={1000}
          value={duration}
          onChange={setDuration}
          marks={{ 1000: '1s', 10000: '10s', 20000: '20s', 30000: '30s' }}
          disabled={disabled || pumpRunning}
        />
      </div>
      <Button
        type="primary"
        block
        loading={loading}
        disabled={disabled || pumpRunning}
        onClick={handleWater}
        style={{ height: 44 }}
      >
        {pumpRunning ? `补水中 (${duration / 1000}秒)...` : '立即补水'}
      </Button>
    </Card>
  );
}
