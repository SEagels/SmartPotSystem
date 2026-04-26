import { useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, Avatar, Dropdown, Typography } from 'antd';
import {
  DashboardOutlined,
  ExperimentOutlined,
  AlertOutlined,
  LogoutOutlined,
  UserOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
} from '@ant-design/icons';
import { useAuth } from '../hooks/useAuth';

const { Header, Sider, Content } = Layout;
const { Text } = Typography;

// 侧边栏导航项：key 与路由路径一一对应，用于高亮当前菜单
const menuItems = [
  { key: '/', icon: <DashboardOutlined />, label: '设备概览' },
  { key: '/plants', icon: <ExperimentOutlined />, label: '植物品种' },
  { key: '/alerts', icon: <AlertOutlined />, label: '告警中心' },
];

// 品牌 Logo：内联 SVG 绿叶图标 + 金色圆点，支持折叠态自动缩放
function PlantLogo({ size = 36 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <rect width="48" height="48" rx="14" fill="rgba(255,255,255,0.15)" />
      <path
        d="M14 38V28C14 24 16 20 20 18"
        stroke="#fff"
        strokeWidth="2.5"
        strokeLinecap="round"
      />
      <path
        d="M20 18C22 14 26 10 32 10C33 12 34 16 33 20C28 20 24 19 20 18Z"
        fill="#A7F3D0"
        stroke="#fff"
        strokeWidth="2"
        strokeLinejoin="round"
      />
      <path
        d="M18 28C14 26 10 28 10 34C10 36 12 38 16 38"
        stroke="#fff"
        strokeWidth="2.5"
        strokeLinecap="round"
      />
      <path
        d="M34 16C38 18 40 22 38 26"
        stroke="#A7F3D0"
        strokeWidth="2.5"
        strokeLinecap="round"
      />
      <circle cx="14" cy="36" r="3" fill="#FBBF24" />
    </svg>
  );
}

// ── 主布局：侧边栏 + 顶栏 + 内容区 ──
// Sider 使用绿色渐变背景，固定在左侧，可折叠
// Header 含折叠按钮 + 用户头像下拉菜单
// Content 渲染嵌套路由的 Outlet（Dashboard / DeviceDetail 等子页面）
// 背景装饰圆：两个超大径向渐变圆在 Content 层底层，营造柔和植物氛围感
export default function AppLayout() {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuth();

  const handleLogout = () => {
    logout();
    navigate('/login', { replace: true });
  };

  // 用户下拉菜单：显示用户名 + 分隔线 + 退出登录（danger 红色样式）
  const userMenu = {
    items: [
      { key: 'profile', icon: <UserOutlined />, label: user?.username ?? '用户' },
      { type: 'divider' as const },
      { key: 'logout', icon: <LogoutOutlined />, label: '退出登录', danger: true },
    ],
    onClick: ({ key }: { key: string }) => {
      if (key === 'logout') handleLogout();
    },
  };

  // 根据当前路径推导侧边栏高亮项——嵌套路由如 /devices/xxx 也需要匹配到概览
  const selectedKey = (() => {
    const path = location.pathname;
    if (path === '/') return '/';
    if (path === '/plants') return '/plants';
    if (path === '/alerts') return '/alerts';
    return '/';
  })();

  return (
    <Layout style={{ minHeight: '100vh' }}>
      {/* 侧边栏：深绿渐变背景，品牌色从深到翠绿，视觉层次分明 */}
      <Sider
        trigger={null}
        collapsible
        collapsed={collapsed}
        style={{
          background: 'linear-gradient(180deg, #14532D 0%, #15803D 40%, #059669 100%)',
          boxShadow: '2px 0 24px rgba(21,128,61,0.15)',
        }}
        width={224}
      >
        <div
          style={{
            height: 64,
            display: 'flex',
            alignItems: 'center',
            justifyContent: collapsed ? 'center' : 'flex-start',
            gap: 10,
            padding: collapsed ? '0' : '0 20px',
            borderBottom: '1px solid rgba(255,255,255,0.1)',
          }}
        >
          <PlantLogo size={collapsed ? 34 : 30} />
          {!collapsed && (
            <div>
              <Text
                strong
                style={{
                  color: '#fff',
                  fontSize: 16,
                  whiteSpace: 'nowrap',
                  fontFamily: 'var(--font-heading)',
                  letterSpacing: '0.02em',
                }}
              >
                SmartPot
              </Text>
              <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.55)', marginTop: -1 }}>
                智能花盆管家
              </div>
            </div>
          )}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          style={{
            background: 'transparent',
            borderInlineEnd: 'none',
            marginTop: 8,
            fontWeight: 500,
          }}
        />
        <div
          style={{
            position: 'absolute',
            bottom: 20,
            left: 0,
            right: 0,
            padding: '0 20px',
            textAlign: 'center',
            opacity: collapsed ? 0 : 1,
            transition: 'opacity 200ms ease-out',
          }}
        >
          <Text style={{ color: 'rgba(255,255,255,0.35)', fontSize: 11 }}>
            v1.2.3 · 运行中
          </Text>
        </div>
      </Sider>
      <Layout>
        <Header
          style={{
            background: '#fff',
            padding: '0 24px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            height: 56,
            boxShadow: '0 1px 6px rgba(21,128,61,0.06)',
            borderBottom: '1px solid #E2EFE7',
            zIndex: 1,
          }}
        >
          <span
            onClick={() => setCollapsed(!collapsed)}
            style={{
              fontSize: 17,
              cursor: 'pointer',
              color: 'var(--color-primary-dark)',
              width: 36,
              height: 36,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: 8,
              transition: 'background 150ms',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.background = '#F0FDF4')}
            onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
          >
            {collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
          </span>
          <Dropdown menu={userMenu} placement="bottomRight">
            <div
              style={{
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                padding: '4px 12px 4px 4px',
                borderRadius: 24,
                transition: 'background 150ms',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.background = '#F0FDF4')}
              onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
            >
              <Avatar
                style={{ background: 'linear-gradient(135deg, #15803D, #22C55E)' }}
                icon={<UserOutlined />}
                size={32}
              />
              <Text style={{ fontSize: 13, color: 'var(--color-text-secondary)' }}>
                {user?.username ?? '用户'}
              </Text>
            </div>
          </Dropdown>
        </Header>
        <Content
          style={{
            background: 'var(--color-bg)',
            overflow: 'auto',
            position: 'relative',
          }}
        >
          {/* 背景装饰层：两个半透明径向渐变圆，营造植物养护的柔和氛围 */}
          <div
            style={{
              position: 'absolute',
              top: -120,
              right: -120,
              width: 400,
              height: 400,
              borderRadius: '50%',
              background: 'radial-gradient(circle, rgba(21,128,61,0.03) 0%, transparent 70%)',
              pointerEvents: 'none',
            }}
          />
          <div
            style={{
              position: 'absolute',
              bottom: -80,
              left: -80,
              width: 300,
              height: 300,
              borderRadius: '50%',
              background: 'radial-gradient(circle, rgba(5,150,105,0.03) 0%, transparent 70%)',
              pointerEvents: 'none',
            }}
          />
          <div style={{ position: 'relative', zIndex: 1 }}>
            <Outlet />
          </div>
        </Content>
      </Layout>
    </Layout>
  );
}
