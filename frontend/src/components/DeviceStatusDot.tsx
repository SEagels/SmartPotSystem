import { Badge } from 'antd';

export default function DeviceStatusDot({ online }: { online: boolean }) {
  return (
    <Badge
      status={online ? 'success' : 'error'}
      text={online ? '在线' : '离线'}
    />
  );
}
