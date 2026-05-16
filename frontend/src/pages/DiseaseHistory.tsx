import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Alert, Card, Typography, Spin, Empty, Table, Tag, Button } from 'antd';
import { getDiseaseHistory, type DiseaseRecord } from '../api/diseases';
import { DISEASE_NAME_MAP } from '../utils/constants';
import { formatDateTime, daysAgo } from '../utils/format';

const { Title } = Typography;

const SEVERITY_COLORS: Record<string, string> = {
  mild: 'gold',
  moderate: 'orange',
  severe: 'red',
};

export default function DiseaseHistory() {
  const { deviceId } = useParams<{ deviceId: string }>();
  const navigate = useNavigate();
  const [records, setRecords] = useState<DiseaseRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!deviceId) return;
    setLoading(true);
    setError(null);
    getDiseaseHistory(deviceId, { start: daysAgo(30), end: new Date().toISOString() })
      .then(setRecords)
      .catch((e: unknown) => {
        setRecords([]);
        setError(e instanceof Error ? e.message : '病害历史数据加载失败');
      })
      .finally(() => setLoading(false));
  }, [deviceId]);

  const columns = [
    {
      title: '时间',
      dataIndex: 'timestamp',
      render: (v: string) => formatDateTime(v),
      width: 160,
    },
    {
      title: '病害名称',
      dataIndex: 'disease_class',
      render: (v: string, r: DiseaseRecord) => (
        <Tag color="red">{DISEASE_NAME_MAP[v] ?? r.disease_name}</Tag>
      ),
    },
    {
      title: '置信度',
      dataIndex: 'confidence',
      render: (v: number) => `${(v * 100).toFixed(0)}%`,
      width: 100,
    },
    {
      title: '严重程度',
      dataIndex: 'severity',
      render: (v: string) => {
        const colors: Record<string, string> = { mild: '轻度', moderate: '中度', severe: '重度' };
        return <Tag color={SEVERITY_COLORS[v] ?? 'default'}>{colors[v] ?? v}</Tag>;
      },
      width: 100,
    },
  ];

  if (loading) {
    return <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh' }}><Spin size="large" /></div>;
  }

  return (
    <div className="page-container">
      <Button type="link" onClick={() => navigate(`/devices/${deviceId}`)} style={{ padding: 0, marginBottom: 8 }}>
        ← 返回设备
      </Button>
      <Title level={4}>病害检测历史</Title>
      {error && (
        <Alert
          type="error"
          showIcon
          message="数据加载失败"
          description={error}
          style={{ marginBottom: 16 }}
        />
      )}
      <Card bordered={false} style={{ borderRadius: 12 }}>
        {!error && records.length === 0 ? (
          <Empty description="近30天无病害记录" />
        ) : records.length > 0 ? (
          <Table
            dataSource={records}
            columns={columns}
            rowKey="detection_id"
            pagination={{ pageSize: 20 }}
            size="middle"
            scroll={{ x: 640 }}
          />
        ) : (
          <Empty description="暂无可显示的数据" />
        )}
      </Card>
    </div>
  );
}
