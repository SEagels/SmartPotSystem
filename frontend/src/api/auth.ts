import client from './client';

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  username: string;
  password: string;
  phone: string;
}

export interface AuthData {
  user_id: string;
  username: string;
  token: string;
  expires_at: string;
}

export interface UserProfile {
  user_id: string;
  username: string;
  phone: string;
  created_at: string;
  device_count: number;
}

export async function login(data: LoginRequest) {
  const res = await client.post('/auth/login', data);
  return res.data.data as AuthData;
}

export async function register(data: RegisterRequest) {
  const res = await client.post('/auth/register', data);
  return res.data.data as AuthData;
}

export async function getProfile() {
  const res = await client.get('/auth/profile');
  return res.data.data as UserProfile;
}
