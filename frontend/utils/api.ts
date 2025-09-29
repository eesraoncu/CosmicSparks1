import axios, { AxiosResponse } from 'axios';
import { 
  Province, 
  DailyStats, 
  User, 
  Alert, 
  SystemStatus,
  UserRegistrationForm,
  UserUpdateForm,
  ApiResponse 
} from '@/types';

// Create axios instance with base configuration
const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for adding auth headers
api.interceptors.request.use(
  (config) => {
    // Add auth token if available (only on client side)
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('auth_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

// API functions
export const apiClient = {
  // Province endpoints
  getProvinces: async (): Promise<Province[]> => {
    const response: AxiosResponse<Province[]> = await api.get('/api/provinces/');
    return response.data;
  },

  getProvince: async (provinceId: number): Promise<Province> => {
    const response: AxiosResponse<Province> = await api.get(`/api/provinces/${provinceId}`);
    return response.data;
  },

  // Stats endpoints
  getStats: async (params?: {
    province_ids?: number[];
    start_date?: string;
    end_date?: string;
    days?: number;
  }): Promise<DailyStats[]> => {
    const response: AxiosResponse<DailyStats[]> = await api.get('/api/stats/', { params });
    return response.data;
  },

  getCurrentStats: async (province_ids?: number[]): Promise<DailyStats[]> => {
    const params = province_ids ? { province_ids } : {};
    const response: AxiosResponse<DailyStats[]> = await api.get('/api/stats/current', { params });
    return response.data;
  },

  getProvinceStats: async (provinceId: number, days: number = 30): Promise<DailyStats[]> => {
    const response: AxiosResponse<DailyStats[]> = await api.get(`/api/stats/province/${provinceId}`, {
      params: { days }
    });
    return response.data;
  },

  // User endpoints
  createUser: async (userData: UserRegistrationForm): Promise<User> => {
    const response: AxiosResponse<User> = await api.post('/api/users/', userData);
    return response.data;
  },

  getUser: async (userId: string): Promise<User> => {
    const response: AxiosResponse<User> = await api.get(`/api/users/${userId}`);
    return response.data;
  },

  updateUser: async (userId: string, userData: UserUpdateForm): Promise<User> => {
    const response: AxiosResponse<User> = await api.put(`/api/users/${userId}`, userData);
    return response.data;
  },

  verifyEmail: async (token: string): Promise<ApiResponse<void>> => {
    const response: AxiosResponse<ApiResponse<void>> = await api.post('/api/users/verify', null, {
      params: { token }
    });
    return response.data;
  },

  unsubscribeUser: async (userId: string): Promise<ApiResponse<void>> => {
    const response: AxiosResponse<ApiResponse<void>> = await api.delete(`/api/users/${userId}`);
    return response.data;
  },

  // Alert endpoints
  getUserAlerts: async (userId: string, days: number = 7): Promise<Alert[]> => {
    const response: AxiosResponse<Alert[]> = await api.get(`/api/alerts/user/${userId}`, {
      params: { days }
    });
    return response.data;
  },

  // System endpoints
  getSystemStatus: async (): Promise<SystemStatus> => {
    const response: AxiosResponse<SystemStatus> = await api.get('/api/system/status');
    return response.data;
  },

  getPipelineLogs: async (days: number = 7): Promise<any[]> => {
    const response: AxiosResponse<any[]> = await api.get('/api/system/pipeline-logs', {
      params: { days }
    });
    return response.data;
  },

  // Health check
  healthCheck: async (): Promise<any> => {
    const response: AxiosResponse<any> = await api.get('/health');
    return response.data;
  },
};

// Utility functions for data processing
export const dataUtils = {
  // Calculate air quality category from PM2.5 value
  getAirQualityCategory: (pm25: number): string => {
    if (pm25 <= 12) return 'Good';
    if (pm25 <= 35) return 'Moderate';
    if (pm25 <= 55) return 'Unhealthy for Sensitive Groups';
    if (pm25 <= 150) return 'Unhealthy';
    if (pm25 <= 250) return 'Very Unhealthy';
    return 'Hazardous';
  },

  // Get alert level from PM2.5 and dust conditions
  getAlertLevel: (pm25: number, dustDetected: boolean = false, dustAod: number = 0): string => {
    if (pm25 >= 150 || (dustDetected && dustAod > 0.6)) return 'extreme';
    if (pm25 >= 75 || (dustDetected && dustAod > 0.4)) return 'high';
    if (pm25 >= 50 || (dustDetected && dustAod > 0.15)) return 'moderate';
    if (pm25 >= 25 || dustAod > 0.05) return 'low';
    return 'none';
  },

  // Format date for display
  formatDate: (dateString: string): string => {
    const date = new Date(dateString);
    return date.toLocaleDateString('tr-TR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  },

  // Format date for API
  formatDateForAPI: (date: Date): string => {
    return date.toISOString().split('T')[0];
  },

  // Get health group description in Turkish
  getHealthGroupDescription: (healthGroup: string): string => {
    const descriptions = {
      general: 'Genel nüfus',
      sensitive: 'Hassas grup (çocuklar, yaşlılar, açık havada çalışanlar)',
      respiratory: 'Solunum hastalığı olanlar (astım, KOAH vb.)',
      cardiac: 'Kalp hastalığı olanlar',
    };
    return descriptions[healthGroup as keyof typeof descriptions] || healthGroup;
  },

  // Get health recommendations based on alert level and health group
  getHealthRecommendations: (alertLevel: string, healthGroup: string): string[] => {
    const recommendations: Record<string, Record<string, string[]>> = {
      none: {
        general: ['Hava kalitesi iyidir', 'Açık hava aktivitelerini rahatlıkla yapabilirsiniz'],
        sensitive: ['Hava kalitesi hassas bireyler için uygundur'],
        respiratory: ['Açık hava aktiviteleri için iyi koşullar'],
        cardiac: ['Tüm aktiviteler için uygun hava kalitesi'],
      },
      low: {
        general: ['Uzun süreli açık hava egzersizini azaltın'],
        sensitive: ['Semptom yaşıyorsanız açık hava aktivitelerini sınırlayın'],
        respiratory: ['Açık havada maske kullanmayı düşünün', 'Semptomlarınızı takip edin'],
        cardiac: ['Yorucu açık hava aktivitelerini sınırlayın'],
      },
      moderate: {
        general: ['Açık hava egzersizini sınırlayın'],
        sensitive: ['Mümkünse içeride kalın'],
        respiratory: ['İçeride kalın', 'Mümkünse hava temizleyici kullanın'],
        cardiac: ['Açık hava aktivitelerinden kaçının', 'Sağlığınızı yakından takip edin'],
      },
      high: {
        general: ['Açık hava aktivitelerinden kaçının'],
        sensitive: ['İçeride kalın', 'Tüm açık hava aktivitelerinden kaçının'],
        respiratory: ['Acil durum koşulları', 'Hava filtreli iç mekanda kalın'],
        cardiac: ['Sağlık acil durumu', 'İçeride kalın ve semptomları takip edin'],
      },
      extreme: {
        general: ['Herkes için tehlikeli hava kalitesi', 'Acil durum koşulları'],
        sensitive: ['Sağlık acil durumu', 'Hava filtreli ortamda kalın'],
        respiratory: ['Tıbbi acil durum', 'Gerekirse sağlık kuruluşuna başvurun'],
        cardiac: ['Tıbbi acil durum', 'Sağlık hizmeti sağlayıcınızla iletişime geçin'],
      },
    };

    return recommendations[alertLevel]?.[healthGroup] || ['Hava kalitesi verisi mevcut değil'];
  },

  // Calculate distance between two coordinates
  calculateDistance: (lat1: number, lon1: number, lat2: number, lon2: number): number => {
    const R = 6371; // Earth's radius in km
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
      Math.sin(dLon / 2) * Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
  },

  // Get nearest province to coordinates
  getNearestProvince: (lat: number, lon: number, provinces: Province[]): Province | null => {
    if (!provinces.length) return null;

    let nearest = provinces[0];
    let minDistance = Infinity;

    // Note: This would need actual province coordinates
    // For now, return first province as placeholder
    return nearest;
  },

  // Validate email format
  isValidEmail: (email: string): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  },

  // Format PM2.5 value for display
  formatPM25: (value: number): string => {
    return `${value.toFixed(1)} μg/m³`;
  },

  // Format AOD value for display
  formatAOD: (value: number): string => {
    return value.toFixed(3);
  },

  // Get dust intensity color
  getDustIntensityColor: (intensity: string): string => {
    const colors = {
      'None': '#10b981',
      'Light': '#fbbf24',
      'Moderate': '#f59e0b',
      'Heavy': '#ef4444',
      'Extreme': '#991b1b',
    };
    return colors[intensity as keyof typeof colors] || '#6b7280';
  },
};

export default api;
