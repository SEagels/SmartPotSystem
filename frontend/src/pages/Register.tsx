import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Form, Input, Button, Card, Typography, message } from 'antd';
import { UserOutlined, LockOutlined, PhoneOutlined } from '@ant-design/icons';
import { register } from '../api/auth';
import { useAuth } from '../hooks/useAuth';

const { Title, Text } = Typography;

export default function Register() {
  const [loading, setLoading] = useState(false);
  const { login: saveAuth } = useAuth();
  const navigate = useNavigate();

  const onFinish = async (values: { username: string; password: string; phone: string }) => {
    setLoading(true);
    try {
      const data = await register(values);
      saveAuth(data);
      message.success('注册成功');
      navigate('/', { replace: true });
    } catch {
      // error handled by interceptor
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
        background: 'linear-gradient(160deg, #F0FDF4 0%, #D1FAE5 30%, #A7F3D0 70%, #86EFAC 100%)',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      <div
        style={{
          position: 'absolute',
          top: -100,
          right: -80,
          width: 480,
          height: 480,
          borderRadius: '50% 60% 40% 70% / 50% 40% 60% 50%',
          background: 'rgba(21,128,61,0.06)',
        }}
      />
      <div
        style={{
          position: 'absolute',
          bottom: -120,
          left: -70,
          width: 440,
          height: 440,
          borderRadius: '60% 40% 55% 45% / 40% 55% 50% 60%',
          background: 'rgba(5,150,105,0.05)',
        }}
      />
      <Card
        style={{
          width: 420,
          borderRadius: 24,
          boxShadow: '0 16px 48px rgba(21,128,61,0.12)',
          border: '1px solid #D1FAE5',
          position: 'relative',
          zIndex: 1,
        }}
        bordered={false}
      >
        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <svg width="56" height="56" viewBox="0 0 56 56" fill="none" style={{ marginBottom: 12 }}>
            <circle cx="28" cy="28" r="28" fill="#F0FDF4" />
            <path d="M18 44V34C18 30 20 26 24 23" stroke="#15803D" strokeWidth="2.5" strokeLinecap="round" />
            <path d="M24 23C26 19 30 15 36 13C37 15 38 18 37 22C33 22 30 20 24 23Z" fill="#A7F3D0" stroke="#15803D" strokeWidth="2" strokeLinejoin="round" />
            <path d="M21 38C16 36 12 38 12 44C12 47 15 49 20 49" stroke="#059669" strokeWidth="2.5" strokeLinecap="round" />
            <circle cx="17" cy="45" r="3" fill="#FBBF24" />
            <path d="M28 11V17" stroke="#22C55E" strokeWidth="2" strokeLinecap="round" opacity="0.6" />
          </svg>
          <Title level={3} style={{ margin: 0, fontFamily: 'var(--font-heading)', color: 'var(--color-primary-dark)' }}>
            创建账号
          </Title>
          <Text type="secondary" style={{ fontSize: 13 }}>加入 SmartPot 智能养护</Text>
        </div>
        <Form layout="vertical" onFinish={onFinish} size="large">
          <Form.Item
            name="username"
            rules={[
              { required: true, message: '请输入用户名' },
              { min: 3, message: '用户名至少3个字符' },
              { max: 32, message: '用户名不超过32个字符' },
              { pattern: /^[a-zA-Z0-9_]+$/, message: '用户名只能包含字母、数字和下划线' },
            ]}
          >
            <Input
              prefix={<UserOutlined style={{ color: '#86A999' }} />}
              placeholder="用户名（3-32位字母/数字/下划线）"
              style={{ borderRadius: 10 }}
            />
          </Form.Item>
          <Form.Item
            name="password"
            rules={[
              { required: true, message: '请输入密码' },
              { min: 6, message: '密码至少6个字符' },
              { max: 64, message: '密码不超过64个字符' },
            ]}
          >
            <Input.Password
              prefix={<LockOutlined style={{ color: '#86A999' }} />}
              placeholder="密码（至少6位）"
              style={{ borderRadius: 10 }}
            />
          </Form.Item>
          <Form.Item
            name="phone"
            rules={[
              { required: true, message: '请输入手机号' },
              { pattern: /^1[3-9]\d{9}$/, message: '手机号格式不正确' },
            ]}
          >
            <Input
              prefix={<PhoneOutlined style={{ color: '#86A999' }} />}
              placeholder="手机号"
              style={{ borderRadius: 10 }}
            />
          </Form.Item>
          <Form.Item style={{ marginBottom: 16 }}>
            <Button type="primary" htmlType="submit" block loading={loading} style={{ borderRadius: 10, height: 44, fontSize: 15 }}>
              注册
            </Button>
          </Form.Item>
        </Form>
        <div style={{ textAlign: 'center' }}>
          <Text type="secondary" style={{ fontSize: 13 }}>已有账号？</Text>{' '}
          <Link to="/login" style={{ fontSize: 13 }}>立即登录</Link>
        </div>
      </Card>
    </div>
  );
}
