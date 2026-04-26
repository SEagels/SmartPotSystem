import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Form, Input, Button, Card, Typography, message } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { login } from '../api/auth';
import { useAuth } from '../hooks/useAuth';

const { Title, Text } = Typography;

// ── 登录页 ──
// 数据流：输入凭证 → login() API 调用 → saveAuth() 写入 Context+localStorage → 跳转首页
// 背景采用植物绿色系渐变 + 有机形态装饰块，传达"自然/养护"品牌感
// replace: true 确保登录后不可通过浏览器后退回到登录页
export default function Login() {
  const [loading, setLoading] = useState(false);
  const { login: saveAuth } = useAuth();
  const navigate = useNavigate();

  const onFinish = async (values: { username: string; password: string }) => {
    setLoading(true);
    try {
      const data = await login(values);
      // 将后端返回的 token + 用户信息同步到 AuthContext（→ localStorage）
      saveAuth(data);
      message.success('登录成功');
      navigate('/', { replace: true });
    } catch {
      // 错误由 Axios 拦截器统一提示
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        // 植物绿色系渐变背景 + 不规格椭圆装饰块，构建品牌自然感
        background: 'linear-gradient(160deg, #F0FDF4 0%, #D1FAE5 30%, #A7F3D0 70%, #86EFAC 100%)',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* 装饰元素：有机形态半透明椭圆，营造植物/自然氛围 */}
      <div
        style={{
          position: 'absolute',
          top: -120,
          left: -80,
          width: 500,
          height: 500,
          borderRadius: '60% 40% 70% 30% / 45% 55% 45% 55%',
          background: 'rgba(21,128,61,0.06)',
        }}
      />
      <div
        style={{
          position: 'absolute',
          bottom: -100,
          right: -60,
          width: 400,
          height: 400,
          borderRadius: '40% 60% 30% 70% / 55% 45% 55% 45%',
          background: 'rgba(5,150,105,0.05)',
        }}
      />
      <Card
        style={{
          width: 400,
          borderRadius: 24,
          boxShadow: '0 16px 48px rgba(21,128,61,0.12)',
          border: '1px solid #D1FAE5',
          position: 'relative',
          zIndex: 1,
        }}
        bordered={false}
      >
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <svg width="56" height="56" viewBox="0 0 56 56" fill="none" style={{ marginBottom: 12 }}>
            <circle cx="28" cy="28" r="28" fill="#F0FDF4" />
            <path d="M14 44V34C14 28 17 24 22 21" stroke="#15803D" strokeWidth="2.5" strokeLinecap="round" />
            <path d="M22 21C25 15 31 11 39 11C40 14 42 18 40 23C34 23 30 21 22 21Z" fill="#A7F3D0" stroke="#15803D" strokeWidth="2" strokeLinejoin="round" />
            <path d="M18 33C14 30 9 33 9 39C9 42 12 45 17 45" stroke="#059669" strokeWidth="2.5" strokeLinecap="round" />
            <circle cx="14" cy="41" r="3.5" fill="#FBBF24" />
          </svg>
          <Title level={3} style={{ margin: 0, fontFamily: 'var(--font-heading)', color: 'var(--color-primary-dark)' }}>
            SmartPot
          </Title>
          <Text type="secondary" style={{ fontSize: 13 }}>智能花盆管理系统</Text>
        </div>
        <Form layout="vertical" onFinish={onFinish} size="large">
          <Form.Item
            name="username"
            rules={[
              { required: true, message: '请输入用户名' },
              { min: 3, message: '用户名至少3个字符' },
            ]}
          >
            <Input prefix={<UserOutlined style={{ color: '#86A999' }} />} placeholder="用户名" style={{ borderRadius: 10 }} />
          </Form.Item>
          <Form.Item
            name="password"
            rules={[
              { required: true, message: '请输入密码' },
              { min: 6, message: '密码至少6个字符' },
            ]}
          >
            <Input.Password prefix={<LockOutlined style={{ color: '#86A999' }} />} placeholder="密码" style={{ borderRadius: 10 }} />
          </Form.Item>
          <Form.Item style={{ marginBottom: 16 }}>
            <Button type="primary" htmlType="submit" block loading={loading} style={{ borderRadius: 10, height: 44, fontSize: 15 }}>
              登录
            </Button>
          </Form.Item>
        </Form>
        <div style={{ textAlign: 'center' }}>
          <Text type="secondary" style={{ fontSize: 13 }}>还没有账号？</Text>{' '}
          <Link to="/register" style={{ fontSize: 13 }}>立即注册</Link>
        </div>
      </Card>
    </div>
  );
}
