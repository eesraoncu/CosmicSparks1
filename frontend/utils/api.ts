import axios, { AxiosResponse } from 'axios';
import { Province, DailyStats, User, Alert, SystemStatus, UserRegistrationForm, UserUpdateForm, ApiResponse } from '@/types';

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('auth_token');
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use((r) => r, (error) => {
  console.error('API Error:', error.response?.data || error.message);
  return Promise.reject(error);
});

export const apiClient = {
  getProvinces: async (): Promise<Province[]> => (await api.get('/api/provinces/')).data,
  getProvince: async (provinceId: number): Promise<Province> => (await api.get(`/api/provinces/${provinceId}`)).data,
  getStats: async (params?: { province_ids?: number[]; start_date?: string; end_date?: string; days?: number; }): Promise<DailyStats[]> => (await api.get('/api/stats/', { params })).data,
  getCurrentStats: async (province_ids?: number[]): Promise<DailyStats[]> => (await api.get('/api/stats/current', { params: province_ids ? { province_ids } : {} })).data,
  getProvinceStats: async (provinceId: number, days: number = 30): Promise<DailyStats[]> => (await api.get(`/api/stats/province/${provinceId}`, { params: { days } })).data,
  createUser: async (userData: UserRegistrationForm): Promise<User> => (await api.post('/api/users/', userData)).data,
  getUser: async (userId: string): Promise<User> => (await api.get(`/api/users/${userId}`)).data,
  updateUser: async (userId: string, userData: UserUpdateForm): Promise<User> => (await api.put(`/api/users/${userId}`, userData)).data,
  verifyEmail: async (token: string): Promise<ApiResponse<void>> => (await api.post('/api/users/verify', null, { params: { token } })).data,
  unsubscribeUser: async (userId: string): Promise<ApiResponse<void>> => (await api.delete(`/api/users/${userId}`)).data,
  getUserAlerts: async (userId: string, days: number = 7): Promise<Alert[]> => (await api.get(`/api/alerts/user/${userId}`, { params: { days } })).data,
  getSystemStatus: async (): Promise<SystemStatus> => (await api.get('/api/system/status')).data,
  getPipelineLogs: async (days: number = 7): Promise<any[]> => (await api.get('/api/system/pipeline-logs', { params: { days } })).data,
  healthCheck: async (): Promise<any> => (await api.get('/health')).data,

  // Auth
  login: async (email: string, password: string): Promise<{ accessToken: string; user: User }> => {
    const r = await api.post('/api/auth/login', { email, password });
    const token = r.data.access_token || r.data.accessToken;
    return { accessToken: token, user: r.data.user };
  },
  register: async (data: { email: string; password: string; province_ids?: number[]; health_group?: string }): Promise<User> => {
    const r = await api.post('/api/auth/register', data);
    return r.data;
  },
  me: async (): Promise<User> => (await api.get('/api/auth/me')).data,
};

export const dataUtils = {
  getAirQualityCategory: (pm25: number): string => pm25 <= 8 ? 'Good' : pm25 <= 15 ? 'Moderate' : pm25 <= 25 ? 'Unhealthy for Sensitive Groups' : pm25 <= 50 ? 'Unhealthy' : pm25 <= 100 ? 'Very Unhealthy' : 'Hazardous',
  getAlertLevel: (pm25: number, dustDetected: boolean = false, dustAod: number = 0): string => {
    if (pm25 >= 50 || (dustDetected && dustAod > 0.6)) return 'extreme';
    if (pm25 >= 25 || (dustDetected && dustAod > 0.4)) return 'high';
    if (pm25 >= 15 || (dustDetected && dustAod > 0.15)) return 'moderate';
    if (pm25 >= 8 || dustAod > 0.05) return 'low';
    return 'none';
  },
  formatDate: (dateString: string): string => new Date(dateString).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' }),
  formatDateForAPI: (date: Date): string => date.toISOString().split('T')[0],
  getHealthGroupDescription: (healthGroup: string): string => {
    const descriptions: Record<string, string> = {
      general: 'General population',
      sensitive: 'Sensitive group (children, elderly, outdoor workers)',
      respiratory: 'People with respiratory diseases (asthma, COPD, etc.)',
      cardiac: 'People with heart disease',
    };
    return descriptions[healthGroup] || healthGroup;
  },
  calculateDistance: (lat1: number, lon1: number, lat2: number, lon2: number): number => {
    const R = 6371; const dLat = (lat2 - lat1) * Math.PI / 180; const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = Math.sin(dLat / 2) ** 2 + Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * Math.sin(dLon / 2) ** 2;
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a)); return R * c;
  },
  getNearestProvince: (_lat: number, _lon: number, provinces: Province[]): Province | null => provinces[0] ?? null,
  isValidEmail: (email: string): boolean => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email),
  formatPM25: (value: number): string => `${value.toFixed(1)} μg/m³`,
  formatAOD: (value: number): string => value.toFixed(3),
  getDustIntensityColor: (intensity: string): string => {
    const colors: Record<string, string> = {
      'None': '#10b981',
      'Light': '#fbbf24',
      'Moderate': '#f59e0b',
      'Heavy': '#ef4444',
      'Extreme': '#991b1b'
    };
    return colors[intensity] || '#6b7280';
  },
};

export default api;


