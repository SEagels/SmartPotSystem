import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { AuthProvider } from './contexts/AuthContext';
import App from './App';
import './styles/global.css';

// ── 应用入口 ──
// Provider 嵌套顺序（外层先初始化）：
//   StrictMode → ConfigProvider(主题/国际化) → BrowserRouter(路由) → AuthProvider(认证) → App(页面树)
// BrowserRouter 必须包裹 AuthProvider，因为 AuthContext 内部的 useNavigate 依赖 Router 上下文
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ConfigProvider
      locale={zhCN}
      theme={{
        token: {
          // 全站主色：植物绿 #4caf50，统一按钮/链接/选中态等所有 Ant Design 组件色调
          colorPrimary: '#4caf50',
          borderRadius: 8,
          fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
        },
      }}
    >
      <BrowserRouter>
        <AuthProvider>
          <App />
        </AuthProvider>
      </BrowserRouter>
    </ConfigProvider>
  </React.StrictMode>,
);
