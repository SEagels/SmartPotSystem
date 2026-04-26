import axios from 'axios';
import { message } from 'antd';
import { API_BASE } from '../utils/constants';

// ── 全局 Axios 实例 ──
// 统一 baseURL + 超时 + JSON 请求头，所有 API 模块（auth/devices/telemetry 等）共用此实例
const client = axios.create({
  baseURL: API_BASE,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

// ── 请求拦截器：自动注入 JWT Bearer Token ──
// AuthContext.login() 将 token 写入 localStorage，此处透传至 Authorization 头
// 上层调用方无需手动携带 Token，减少重复代码
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ── 响应拦截器：两层错误处理 ──
// 第一层：HTTP 200 但业务 code ≠ 0 → 后端的业务错误（如设备不存在），统一 message.error
// 第二层：HTTP 4xx/5xx → 按状态码分类：
//   · 401 / code=1002 → Token 失效，清除缓存并硬跳转到登录页
//   · 422 → FastAPI 参数校验失败，提取 loc 路径拼成 "字段名: 错误信息" 友好提示
//   · 其他 → 优先取后端 message，其次取 detail，最后 fallback
client.interceptors.response.use(
  (res) => {
    // 后端统一响应格式 { code, message, data }，code !== 0 表示业务失败
    if (res.data && typeof res.data.code === 'number' && res.data.code !== 0) {
      message.error(res.data.message || '请求失败');
      return Promise.reject(new Error(res.data.message || '请求失败'));
    }
    return res;
  },
  (err) => {
    // Token 过期或无效 → 清空本地认证状态，硬跳转（不用 navigate 因拦截器不在组件树内）
    if (err.response?.status === 401 || err.response?.data?.code === 1002) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }

    // FastAPI 422: 将 Pydantic 校验错误的 loc 路径转换为中文友好提示
    if (err.response?.status === 422 && err.response?.data?.detail) {
      const details = err.response.data.detail;
      if (Array.isArray(details)) {
        const msgs = details
          .filter((d: { loc: string[]; msg: string }) => d.loc.length > 1)
          .map((d: { loc: string[]; msg: string }) => `${d.loc.slice(1).join('.')}: ${d.msg}`);
        if (msgs.length > 0) {
          msgs.forEach((m: string) => message.error(m));
          return Promise.reject(err);
        }
      }
    }

    // 通用错误兜底
    const msg = err.response?.data?.message || err.response?.data?.detail || err.message || '请求失败';
    message.error(typeof msg === 'string' ? msg : '请求参数不符合要求');
    return Promise.reject(err);
  },
);

// 后端统一响应结构泛型，供各 API 模块声明返回值类型
export interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
  meta?: { page: number; page_size: number; total: number };
}

export default client;
