import { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Typography, Spin, Descriptions, Tag, Empty, Button, Row, Col } from 'antd';
import { getImageDetail, type ImageDetail as ImageDetailType } from '../api/images';
import { DISEASE_NAME_MAP } from '../utils/constants';
import { formatDateTime } from '../utils/format';
import BBoxOverlay from '../components/BBoxOverlay';
import HealthGauge from '../components/HealthGauge';

const { Title, Text, Paragraph } = Typography;

const SEVERITY_LABELS: Record<string, { color: string; label: string }> = {
  mild: { color: 'gold', label: '轻微' },
  moderate: { color: 'orange', label: '中等' },
  severe: { color: 'red', label: '严重' },
};

export default function ImageDetail() {
  const { deviceId, imageId } = useParams<{ deviceId: string; imageId: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<ImageDetailType | null>(null);
  const [loading, setLoading] = useState(true);
  const [imgSize, setImgSize] = useState({ w: 800, h: 600 });
  const imgRef = useRef<HTMLImageElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!deviceId || !imageId) return;
    getImageDetail(deviceId, imageId)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [deviceId, imageId]);

  const handleImgLoad = () => {
    if (imgRef.current && containerRef.current) {
      setImgSize({
        w: imgRef.current.naturalWidth,
        h: imgRef.current.naturalHeight,
      });
    }
  };

  if (loading) {
    return <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh' }}><Spin size="large" /></div>;
  }

  if (!data) return <Empty description="图像未找到" />;

  const displayWidth = containerRef.current?.clientWidth ?? 800;
  const displayHeight = (imgSize.h / imgSize.w) * displayWidth;

  return (
    <div className="page-container">
      <Button type="link" onClick={() => navigate(`/devices/${deviceId}/images`)} style={{ padding: 0, marginBottom: 16 }}>
        ← 返回图像列表
      </Button>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={16}>
          <Card bordered={false} style={{ borderRadius: 16 }}>
            <div ref={containerRef} style={{ position: 'relative', overflow: 'hidden', borderRadius: 8 }}>
              <img
                ref={imgRef}
                src={data.url}
                alt={`Plant photo ${data.photo_index}`}
                style={{ width: '100%', display: 'block' }}
                onLoad={handleImgLoad}
              />
              {data.detection?.diseases.map((d, i) => (
                <BBoxOverlay
                  key={i}
                  bbox={d.bbox}
                  imageWidth={imgSize.w}
                  imageHeight={imgSize.h}
                  displayWidth={displayWidth}
                  displayHeight={displayHeight}
                  label={`${DISEASE_NAME_MAP[d.class] ?? d.name_zh} ${(d.confidence * 100).toFixed(0)}%`}
                />
              ))}
            </div>
          </Card>
        </Col>

        <Col xs={24} lg={8}>
          <Card bordered={false} style={{ borderRadius: 16, marginBottom: 16 }}>
            <Title level={5}>图像信息</Title>
            <Descriptions column={1} size="small">
              <Descriptions.Item label="拍摄时间">{formatDateTime(data.timestamp)}</Descriptions.Item>
              <Descriptions.Item label="连拍序号">第 {data.photo_index} 张</Descriptions.Item>
              <Descriptions.Item label="质量评分">{data.quality_score?.toFixed(2) ?? '--'}</Descriptions.Item>
            </Descriptions>
          </Card>

          {data.detection ? (
            <>
              <Card bordered={false} style={{ borderRadius: 16, marginBottom: 16, textAlign: 'center' }}>
                <Title level={5}>健康评分</Title>
                <div style={{ display: 'flex', justifyContent: 'center' }}>
                  <HealthGauge score={data.detection.health_score} size={120} />
                </div>
              </Card>

              {data.detection.diseases.length > 0 && (
                <Card bordered={false} style={{ borderRadius: 16 }}>
                  <Title level={5}>检测结果</Title>
                  {data.detection.diseases.map((d, i) => {
                    const sev = SEVERITY_LABELS[d.severity] ?? SEVERITY_LABELS.mild;
                    return (
                      <Card key={i} size="small" style={{ marginBottom: 12, borderRadius: 8 }} bordered>
                        <div style={{ marginBottom: 8 }}>
                          <Tag color="red">{DISEASE_NAME_MAP[d.class] ?? d.name_zh}</Tag>
                          <Tag color={sev.color}>{sev.label}</Tag>
                          <Tag>置信度 {(d.confidence * 100).toFixed(0)}%</Tag>
                        </div>
                        <Paragraph type="secondary" style={{ fontSize: 13, marginBottom: 0 }}>
                          {d.recommendation}
                        </Paragraph>
                      </Card>
                    );
                  })}
                </Card>
              )}

              {data.detection.diseases.length === 0 && (
                <Card bordered={false} style={{ borderRadius: 16 }}>
                  <Tag color="green">未检测到病害</Tag>
                </Card>
              )}
            </>
          ) : (
            <Card bordered={false} style={{ borderRadius: 16 }}>
              <Tag>检测状态：{data.detection ? '已完成' : '等待检测'}</Tag>
            </Card>
          )}
        </Col>
      </Row>
    </div>
  );
}
