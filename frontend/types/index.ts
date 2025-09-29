// API Response Types
export interface Province {
  id: number;
  name: string;
  name_en?: string;
  region?: string;
  population?: number;
  area_km2?: number;
}

export interface DailyStats {
  date: string;
  province_id: number;
  aod_mean?: number;
  aod_max?: number;
  aod_p95?: number;
  dust_aod_mean?: number;
  dust_event_detected?: boolean;
  dust_intensity?: string;
  pm25?: number;
  pm25_lower?: number;
  pm25_upper?: number;
  air_quality_category?: string;
  rh_mean?: number;
  blh_mean?: number;
  data_quality_score?: number;
}

export interface User {
  id: string;
  email: string;
  health_group: HealthGroup;
  province_ids: number[];
  pm25_low_threshold: number;
  pm25_moderate_threshold: number;
  pm25_high_threshold: number;
  dust_aod_threshold: number;
  notify_forecast: boolean;
  notify_current: boolean;
  quiet_hours_start: number;
  quiet_hours_end: number;
  max_alerts_per_day: number;
  is_active: boolean;
  email_verified: boolean;
  created_at: string;
}

export interface Alert {
  id: string;
  province_id: number;
  alert_level: AlertLevel;
  pm25_value: number;
  dust_detected: boolean;
  dust_intensity?: string;
  health_message: string;
  created_at: string;
}

export interface SystemStatus {
  date: string;
  components: Record<string, ComponentStatus>;
  overall_status: 'healthy' | 'degraded';
}

export interface ComponentStatus {
  status: 'success' | 'warning' | 'error';
  message: string;
  data_coverage_pct?: number;
  updated_at: string;
}

// Enums
export enum HealthGroup {
  GENERAL = 'general',
  SENSITIVE = 'sensitive',
  RESPIRATORY = 'respiratory',
  CARDIAC = 'cardiac',
}

export enum AlertLevel {
  NONE = 'none',
  LOW = 'low',
  MODERATE = 'moderate',
  HIGH = 'high',
  EXTREME = 'extreme',
}

export enum AirQuality {
  GOOD = 'Good',
  MODERATE = 'Moderate',
  UNHEALTHY_SENSITIVE = 'Unhealthy for Sensitive Groups',
  UNHEALTHY = 'Unhealthy',
  VERY_UNHEALTHY = 'Very Unhealthy',
  HAZARDOUS = 'Hazardous',
}

// Form Types
export interface UserRegistrationForm {
  email: string;
  health_group: HealthGroup;
  province_ids: number[];
  pm25_low_threshold?: number;
  pm25_moderate_threshold?: number;
  pm25_high_threshold?: number;
  dust_aod_threshold?: number;
  notify_forecast?: boolean;
  notify_current?: boolean;
  quiet_hours_start?: number;
  quiet_hours_end?: number;
  max_alerts_per_day?: number;
}

export interface UserUpdateForm {
  health_group?: HealthGroup;
  province_ids?: number[];
  pm25_low_threshold?: number;
  pm25_moderate_threshold?: number;
  pm25_high_threshold?: number;
  dust_aod_threshold?: number;
  notify_forecast?: boolean;
  notify_current?: boolean;
  quiet_hours_start?: number;
  quiet_hours_end?: number;
  max_alerts_per_day?: number;
  is_active?: boolean;
}

// Map Types
export interface MapBounds {
  north: number;
  south: number;
  east: number;
  west: number;
}

export interface ProvinceMapData extends Province {
  stats?: DailyStats;
  alertLevel?: AlertLevel;
  center: [number, number];
}

// Chart Types
export interface ChartDataPoint {
  date: string;
  pm25?: number;
  aod?: number;
  dust_aod?: number;
  air_quality?: string;
}

export interface TimeSeriesData {
  province_id: number;
  province_name: string;
  data: ChartDataPoint[];
}

// Utility Types
export interface ApiResponse<T> {
  data?: T;
  error?: string;
  message?: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface FilterOptions {
  provinces?: number[];
  startDate?: string;
  endDate?: string;
  alertLevel?: AlertLevel;
  healthGroup?: HealthGroup;
}

// Constants
export const TURKEY_BOUNDS: MapBounds = {
  north: 42.5,
  south: 35.5,
  east: 45.0,
  west: 25.5,
};

export const PROVINCE_CENTERS: Record<number, [number, number]> = {
  1: [41.0082, 28.9784], // İstanbul
  2: [39.9334, 32.8597], // Ankara
  3: [38.4237, 27.1428], // İzmir
  4: [40.1885, 29.0610], // Bursa
  5: [36.8969, 30.7133], // Antalya
  6: [37.0000, 35.3213], // Adana
  7: [37.8746, 32.4932], // Konya
  8: [37.1674, 38.7955], // Şanlıurfa
  9: [37.0662, 37.3833], // Gaziantep
  10: [40.8533, 29.8815], // Kocaeli
};

export const HEALTH_GROUP_LABELS: Record<HealthGroup, string> = {
  [HealthGroup.GENERAL]: 'Genel Nüfus',
  [HealthGroup.SENSITIVE]: 'Hassas Grup (Çocuk, Yaşlı)',
  [HealthGroup.RESPIRATORY]: 'Solunum Hastası',
  [HealthGroup.CARDIAC]: 'Kalp Hastası',
};

export const ALERT_LEVEL_LABELS: Record<AlertLevel, string> = {
  [AlertLevel.NONE]: 'Normal',
  [AlertLevel.LOW]: 'Düşük Risk',
  [AlertLevel.MODERATE]: 'Orta Risk',
  [AlertLevel.HIGH]: 'Yüksek Risk',
  [AlertLevel.EXTREME]: 'Ekstrem Risk',
};

export const ALERT_LEVEL_COLORS: Record<AlertLevel, string> = {
  [AlertLevel.NONE]: '#10b981',
  [AlertLevel.LOW]: '#fbbf24',
  [AlertLevel.MODERATE]: '#f59e0b',
  [AlertLevel.HIGH]: '#ef4444',
  [AlertLevel.EXTREME]: '#991b1b',
};

export const AIR_QUALITY_COLORS: Record<string, string> = {
  'Good': '#10b981',
  'Moderate': '#f59e0b',
  'Unhealthy for Sensitive Groups': '#f59e0b',
  'Unhealthy': '#ef4444',
  'Very Unhealthy': '#991b1b',
  'Hazardous': '#7c2d12',
};

export const PM25_THRESHOLDS = {
  good: 12,
  moderate: 35,
  unhealthy_sensitive: 55,
  unhealthy: 150,
  very_unhealthy: 250,
  hazardous: 500,
};

export const DUST_INTENSITY_LABELS: Record<string, string> = {
  'None': 'Yok',
  'Light': 'Hafif',
  'Moderate': 'Orta',
  'Heavy': 'Yoğun',
  'Extreme': 'Ekstrem',
};
