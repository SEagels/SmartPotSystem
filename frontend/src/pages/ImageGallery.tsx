import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Row, Col, Card, Typography, Spin, Empty, Image, Tag, DatePicker, Button, message, Popconfirm, Upload } from 'antd';
import { EyeOutlined, ReloadOutlined, UploadOutlined } from '@ant-design/icons';
import { getImages, reDetectImages, uploadImage, type ImageItem } from '../api/images';
import { formatDateTime, formatDate } from '../utils/format';

const { Title, Text } = Typography;

const STATUS_CONFIG: Record<string, { color: string; label: string }> = {
  pending_detection: { color: 'default', label: '等待检测' },
  processing: { color: 'processing', label: '检测中' },
  completed: { color: 'success', label: '检测完成' },
  failed: { color: 'error', label: '检测失败' },
};

export default function ImageGallery() {
  const { deviceId } = useParams<{ deviceId: string }>();
  const navigate = useNavigate();
  const [images, setImages] = useState<ImageItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [date, setDate] = useState<string | null>(null);
  const [reDetecting, setReDetecting] = useState(false);
  const [uploading, setUploading] = useState(false);

  // 七天清除：记录最新访问时间
  useEffect(() => {
    if (!deviceId) return;
    const key = `smartpot_images_last_visit_${deviceId}`;
    const lastVisit = localStorage.getItem(key);
    const now = Date.now();
    if (lastVisit) {
      const elapsed = now - parseInt(lastVisit, 10);
      if (elapsed > 7 * 24 * 60 * 60 * 1000) {
        localStorage.removeItem(key);
      }
    }
    localStorage.setItem(key, String(now));
  }, [deviceId]);

  const fetchImages = () => {
    if (!deviceId) return;
    setLoading(true);
    getImages(deviceId, date ?? undefined)
      .then(setImages)
      .catch(() => setImages([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchImages();
  }, [deviceId, date]);

  const handleReDetect = async () => {
    if (!deviceId) return;
    setReDetecting(true);
    try {
      const res = await reDetectImages(deviceId);
      message.success(res.message || '重新检测已启动');
      setTimeout(() => fetchImages(), 2000);
    } catch {
      message.error('重新检测请求失败');
    } finally {
      setReDetecting(false);
    }
  };

  const handleUpload = async (file: File) => {
    if (!deviceId) return;
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('image', file);
      await uploadImage(deviceId, formData);
      message.success('上传成功');
      fetchImages();
    } catch {
      message.error('上传失败');
    } finally {
      setUploading(false);
    }
  };

  if (loading) {
    return <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh' }}><Spin size="large" /></div>;
  }

  return (
    <div className="page-container">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <Button type="link" onClick={() => navigate(`/devices/${deviceId}`)} style={{ padding: 0 }}>
            ← 返回设备
          </Button>
          <Title level={4} style={{ margin: '8px 0 0' }}>叶片图像</Title>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <DatePicker
            onChange={(d) => setDate(d ? formatDate(d.toISOString()) : null)}
            placeholder="按日期筛选"
          />
          <Upload
            accept="image/*"
            showUploadList={false}
            beforeUpload={(file) => {
              handleUpload(file);
              return false;
            }}
          >
            <Button icon={<UploadOutlined />} loading={uploading}>
              上传图片
            </Button>
          </Upload>
          <Popconfirm
            title="重新检测"
            description="将当前设备所有已完成/失败的图像重置为等待检测状态，使用新模型推理。确定要继续吗？"
            onConfirm={handleReDetect}
            okText="确定"
            cancelText="取消"
          >
            <Button icon={<ReloadOutlined />} loading={reDetecting}>
              重新检测
            </Button>
          </Popconfirm>
        </div>
      </div>

      {images.length === 0 ? (
        <Card bordered={false} style={{ borderRadius: 12 }}><Empty description="暂无图像" /></Card>
      ) : (
        <Row gutter={[16, 16]}>
          {images.map((img) => {
            const status = STATUS_CONFIG[img.detection_status] ?? STATUS_CONFIG.pending_detection;
            return (
              <Col xs={24} sm={12} md={8} lg={6} key={img.image_id}>
                <Card
                  hoverable
                  bordered={false}
                  style={{ borderRadius: 12, overflow: 'hidden' }}
                  cover={
                    <div style={{ height: 200, overflow: 'hidden', position: 'relative', background: '#f5f5f5' }}>
                      <Image
                        src={img.url}
                        alt={`Photo ${img.photo_index}`}
                        style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                        preview={false}
                        fallback="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgZmlsbD0iI2Y1ZjVmNSIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBkb21pbmFudC1iYXNlbGluZT0ibWlkZGxlIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmaWxsPSIjYmZiZmJmIiBmb250LXNpemU9IjE2Ij7mr4/mnK/lm77niYc8L3RleHQ+PC9zdmc+"
                      />
                      <Tag
                        color={status.color}
                        style={{ position: 'absolute', top: 8, right: 8 }}
                      >
                        {status.label}
                      </Tag>
                    </div>
                  }
                  onClick={() => navigate(`/devices/${deviceId}/images/${img.image_id}`)}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Text style={{ fontSize: 12 }} type="secondary">
                      {formatDateTime(img.timestamp)}
                    </Text>
                    {img.detection_status === 'completed' && (
                      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                        {img.disease_count > 0 && (
                          <Tag color="red">{img.disease_count} 病害</Tag>
                        )}
                        {img.health_score != null && (
                          <Text strong style={{ color: img.health_score >= 80 ? '#4caf50' : '#fa8c16' }}>
                            {img.health_score}分
                          </Text>
                        )}
                      </div>
                    )}
                  </div>
                  <EyeOutlined style={{ marginLeft: 8, color: '#8c8c8c' }} />
                </Card>
              </Col>
            );
          })}
        </Row>
      )}
    </div>
  );
}
