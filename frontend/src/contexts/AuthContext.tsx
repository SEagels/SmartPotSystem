import { createContext, useState, useCallback, useEffect, type ReactNode } from 'react';
import type { AuthData, UserProfile } from '../api/auth';
import { getProfile } from '../api/auth';

export interface AuthState {
  token: string | null;
  user: UserProfile | null;
  loading: boolean;
  login: (data: AuthData) => void;
  logout: () => void;
  refreshProfile: () => Promise<void>;
}

// 默认值仅为类型占位——Provider 始终在 App 外层挂载，子组件不会消费此默认值
export const AuthContext = createContext<AuthState>({
  token: null,
  user: null,
  loading: true,
  login: () => {},
  logout: () => {},
  refreshProfile: async () => {},
});

// ── 认证状态 Provider ──
// 三层数据流：localStorage（持久层）↔ React state（驱动层）↔ Context（分发层）
//   登录：API 返回 token → 同步写入 localStorage + state → 所有订阅组件感知
//   刷新：页面初始化时若有缓存 token，调用 /profile 获取完整用户信息
//   登出：清除 localStorage + 重置 state → ProtectedRoute 检测到 token===null 自动跳转登录
export function AuthProvider({ children }: { children: ReactNode }) {
  // lazy initializer：从 localStorage 恢复状态，支持页面刷新后免登录
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('token'));
  const [user, setUser] = useState<UserProfile | null>(() => {
    const u = localStorage.getItem('user');
    return u ? JSON.parse(u) : null;
  });
  // 有缓存 token 时进入 loading 态，等 profile 接口返回后再放行渲染（防止闪出登录页）
  const [loading, setLoading] = useState(!!token);

  // login 为同步操作：网络请求在调用方（Login 页面）完成，此处只管状态同步
  const login = useCallback((data: AuthData) => {
    const userInfo = {
      user_id: data.user_id,
      username: data.username,
    };
    localStorage.setItem('token', data.token);
    localStorage.setItem('user', JSON.stringify(userInfo));
    setToken(data.token);
    setUser(userInfo as UserProfile);
  }, []);

  // 初始化/刷新时拉取最新 Profile，失败则静默保留旧缓存（网络波动不影响使用）
  const refreshProfile = useCallback(async () => {
    try {
      const profile = await getProfile();
      setUser(profile);
      localStorage.setItem('user', JSON.stringify(profile));
    } catch {
      // 静默失败：保留 localStorage 中的旧用户数据兜底
    }
  }, []);

  // 登出同步清除所有状态，ProtectedRoute 检测到 token===null 自动拦截
  const logout = useCallback(() => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setToken(null);
    setUser(null);
  }, []);

  // 启动时校验：有 token 则异步拉 Profile，加载完成后才渲染受保护页面
  useEffect(() => {
    if (token) {
      refreshProfile().finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, [token, refreshProfile]);

  return (
    <AuthContext.Provider value={{ token, user, loading, login, logout, refreshProfile }}>
      {children}
    </AuthContext.Provider>
  );
}
