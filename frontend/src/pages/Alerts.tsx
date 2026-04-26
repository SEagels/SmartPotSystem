import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Typography, Spin, Empty, Tabs, Button, Space, Tag, List } from 'antd';
import { BellOutlined, CheckOutlined } from '@ant-design/icons';
import { getAlerts, markAlertRead, markAllAlertsRead, type AlertItem } from '../api/alerts';
import { ALERT_TYPE_LABELS, SEVERITY_COLORS } from '../utils/constants';
import { formatDateTime } from '../utils/format';
import { getDevices, type DeviceListItem } from '../api/devices';
import { useWebSocket } from '../hooks/useWebSocket';

const { Title, Text, Paragraph } = Typography;

export default function Alerts() {
  const navigate = useNavigate();
  const [devices, setDevices] = useState<DeviceListItem[]>([]);
  const [allAlerts, setAllAlerts] = useState<Record<string, AlertItem[]>>({});
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState('all');

  const fetchAll = useCallback(async () => {
    try {
      const devs = await getDevices();
      setDevices(devs);
      const alertMap: Record<string, AlertItem[]> = {};
      await Promise.all(
        devs.map(async (d) => {
          try {
            const { data } = await getAlerts(d.device_id, { page_size: 50 });
            alertMap[d.device_id] = data;
          } catch {
            alertMap[d.device_id] = [];
          }
        }),
      );
      setAllAlerts(alertMap);
    } catch {
      // handled
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  useWebSocket(useCallback((event, deviceId) => {
    if (event === 'alert_new') {
      fetchAll();
    }
  }, [fetchAll]));

  const handleMarkRead = async (alertId: string, deviceId: string) => {
    try {
      await markAlertRead(alertId);
      setAllAlerts((prev) => ({
        ...prev,
        [deviceId]: prev[deviceId]?.map((a) =>
          a.alert_id === alertId ? { ...a, read: true } : a,
        ) ?? [],
      }));
    } catch { /* handled */ }
  };

  const handleMarkAllRead = async (deviceId: string) => {
    try {
      await markAllAlertsRead(deviceId);
      setAllAlerts((prev) => ({
        ...prev,
        [deviceId]: prev[deviceId]?.map((a) => ({ ...a, read: true })) ?? [],
      }));
    } catch { /* handled */ }
  };

  const flattenAlerts = (deviceId?: string): (AlertItem & { device_id: string })[] => {
    const entries = deviceId ? [[deviceId, allAlerts[deviceId] ?? []] as const] : Object.entries(allAlerts);
    return entries.flatMap(([did, alerts]) =>
      alerts.map((a) => ({ ...a, device_id: did })),
    );
  };

  const filteredAlerts = flattenAlerts().filter((a) => {
    if (tab === 'unread') return !a.read;
    if (tab === 'read') return a.read;
    return true;
  });

  const unreadCount = flattenAlerts().filter((a) => !a.read).length;

  if (loading) {
    return <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh' }}><Spin size="large" /></div>;
  }

  return (
    <div className="page-container">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>
          告警中心
          {unreadCount > 0 && <Tag color="red" style={{ marginLeft: 8 }}>{unreadCount} 未读</Tag>}
        </Title>
      </div>

      <Card bordered={false} style={{ borderRadius: 12 }}>
        <Tabs
          activeKey={tab}
          onChange={setTab}
          items={[
            { key: 'all', label: '全部' },
            { key: 'unread', label: `未读 (${flattenAlerts().filter((a) => !a.read).length})` },
            { key: 'read', label: '已读' },
          ]}
        />

        {filteredAlerts.length === 0 ? (
          <Empty description="暂无告警" />
        ) : (
          <List
            dataSource={filteredAlerts}
            renderItem={(alert) => {
              const device = devices.find((d) => d.device_id === alert.device_id);
              return (
                <List.Item
                  key={alert.alert_id}
                  style={{ padding: '16px 0' }}
                  actions={[
                    !alert.read && (
                      <Button
                        type="link"
                        icon={<CheckOutlined />}
                        onClick={() => handleMarkRead(alert.alert_id, alert.device_id)}
                      >
                        标记已读
                      </Button>
                    ),
                    <Button
                      type="link"
                      onClick={() => navigate(`/devices/${alert.device_id}`)}
                    >
                      查看设备
                    </Button>,
                  ].filter(Boolean)}
                >
                  <List.Item.Meta
                    avatar={
                      <div>
                        <span className={`alert-dot ${alert.read ? '' : 'unread'}`} />
                      </div>
                    }
                    title={
                      <Space>
                        <Tag color={SEVERITY_COLORS[alert.severity]}>{alert.severity}</Tag>
                        <Tag>{ALERT_TYPE_LABELS[alert.type] ?? alert.type}</Tag>
                        <Text strong>{alert.title}</Text>
                        {device && <Text type="secondary">({device.name})</Text>}
                      </Space>
                    }
                    description={
                      <div>
                        <Paragraph style={{ marginBottom: 4, fontSize: 13 }}>{alert.message}</Paragraph>
                        <Text type="secondary" style={{ fontSize: 11 }}>
                          {formatDateTime(alert.created_at)}
                        </Text>
                      </div>
                    }
                  />
                </List.Item>
              );
            }}
          />
        )}
      </Card>
    </div>
  );
}
