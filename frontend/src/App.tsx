import { Routes, Route, Navigate } from 'react-router-dom';
import { Spin } from 'antd';
import { useAuth } from './hooks/useAuth';
import AppLayout from './components/AppLayout';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import DeviceDetail from './pages/DeviceDetail';
import ImageGallery from './pages/ImageGallery';
import ImageDetail from './pages/ImageDetail';
import DiseaseHistory from './pages/DiseaseHistory';
import Alerts from './pages/Alerts';
import Reports from './pages/Reports';
import PlantTypes from './pages/PlantTypes';
import DeviceSettings from './pages/DeviceSettings';

// ── 路由守卫 ──
// loading 阶段渲染全屏 Spin，避免 token 校验未完成时闪出登录页
// 未认证时使用 replace 导航，替换历史记录防止用户点返回又回到受保护页面
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { token, loading } = useAuth();
  if (loading) return <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}><Spin size="large" /></div>;
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

// ── 路由定义 ──
// 嵌套路由设计：/ 下 AppLayout 作为父布局（含侧边栏+顶栏），子页面通过 Outlet 渲染
// 所有 /devices/:deviceId/* 子路由共享同一个 URL 参数，方便组件内通过 useParams 获取
export default function App() {
  return (
    <Routes>
      {/* 公开路由：无需登录 */}
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      {/* 受保护路由：ProtectedRoute 包装 AppLayout，统一拦截未登录访问 */}
      <Route path="/" element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
        <Route index element={<Dashboard />} />
        <Route path="devices/:deviceId" element={<DeviceDetail />} />
        <Route path="devices/:deviceId/images" element={<ImageGallery />} />
        <Route path="devices/:deviceId/images/:imageId" element={<ImageDetail />} />
        <Route path="devices/:deviceId/diseases" element={<DiseaseHistory />} />
        <Route path="devices/:deviceId/reports" element={<Reports />} />
        <Route path="devices/:deviceId/settings" element={<DeviceSettings />} />
        <Route path="alerts" element={<Alerts />} />
        <Route path="plants" element={<PlantTypes />} />
      </Route>
      {/* 兜底路由：未匹配路径统一重定向首页 */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
