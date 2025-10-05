export type Province = { id: number; name: string; name_en?: string; region?: string; population?: number; area_km2?: number; };
export type DailyStats = {
  date: string; province_id: number; aod_mean?: number; aod_max?: number; aod_p95?: number; dust_aod_mean?: number; dust_event_detected?: boolean; dust_intensity?: string; pm25?: number; pm25_lower?: number; pm25_upper?: number; air_quality_category?: string; rh_mean?: number; blh_mean?: number; data_quality_score?: number;
};
export type User = { id: string; email: string; health_group: string; province_ids: number[]; pm25_low_threshold: number; pm25_moderate_threshold: number; pm25_high_threshold: number; dust_aod_threshold: number; notify_forecast: boolean; notify_current: boolean; quiet_hours_start: number; quiet_hours_end: number; max_alerts_per_day: number; is_active: boolean; email_verified: boolean; created_at: string; };
export type Alert = { id: string; province_id: number; alert_level: string; pm25_value: number; dust_detected: boolean; dust_intensity?: string; health_message: string; created_at: string; };
export type SystemStatus = { date: string; components: Record<string, { status: string; message: string; data_coverage_pct?: number; updated_at: string }>; overall_status: string; };
export type UserRegistrationForm = { email: string; health_group: 'general'|'sensitive'|'respiratory'|'cardiac'; province_ids: number[]; pm25_low_threshold?: number; pm25_moderate_threshold?: number; pm25_high_threshold?: number; dust_aod_threshold?: number; notify_forecast?: boolean; notify_current?: boolean; quiet_hours_start?: number; quiet_hours_end?: number; max_alerts_per_day?: number; };
export type UserUpdateForm = Partial<Omit<UserRegistrationForm, 'email'|'province_ids'>> & { province_ids?: number[] };
export type ApiResponse<T> = { message?: string; data?: T };

// Minimal centers mapping; map falls back to Ankara if missing
export const PROVINCE_CENTERS: Record<number, [number, number]> = {
  1: [37.0, 35.32], // Adana
  2: [37.76, 38.28], // Adiyaman
  3: [38.76, 30.54], // Afyonkarahisar
  4: [39.72, 43.05], // Agri
  5: [40.65, 35.83], // Amasya
  6: [39.93, 32.86], // Ankara
  7: [36.90, 30.71], // Antalya
  8: [41.18, 41.82], // Artvin
  9: [37.84, 27.84], // Aydin
  10: [39.65, 27.89], // Balikesir
  11: [40.14, 29.98], // Bilecik
  12: [38.89, 40.50], // Bingol
  13: [38.40, 42.11], // Bitlis
  14: [40.73, 31.61], // Bolu
  15: [37.72, 30.29], // Burdur
  16: [40.20, 29.06], // Bursa
  17: [40.15, 26.41], // Canakkale
  18: [40.60, 33.62], // Cankiri
  19: [40.55, 34.95], // Corum
  20: [37.78, 29.09], // Denizli
  21: [37.92, 40.23], // Diyarbakir
  22: [41.68, 26.56], // Edirne
  23: [38.68, 39.22], // Elazig
  24: [39.75, 39.49], // Erzincan
  25: [39.90, 41.27], // Erzurum
  26: [39.78, 30.52], // Eskisehir
  27: [37.06, 37.38], // Gaziantep
  28: [40.92, 38.39], // Giresun
  29: [40.46, 39.48], // Gumushane
  30: [37.58, 43.74], // Hakkari
  31: [36.20, 36.16], // Hatay
  32: [37.77, 30.55], // Isparta
  33: [36.80, 34.64], // Mersin
  34: [41.01, 28.98], // Istanbul
  35: [38.42, 27.14], // Izmir
  36: [40.60, 43.10], // Kars
  37: [41.38, 33.78], // Kastamonu
  38: [38.73, 35.48], // Kayseri
  39: [41.74, 27.22], // Kirklareli
  40: [39.15, 34.16], // Kirsehir
  41: [40.85, 29.88], // Kocaeli
  42: [37.87, 32.49], // Konya
  43: [39.42, 29.98], // Kutahya
  44: [38.35, 38.33], // Malatya
  45: [38.61, 27.43], // Manisa
  46: [37.58, 36.93], // Kahramanmaras
  47: [37.32, 40.74], // Mardin
  48: [37.22, 28.37], // Mugla
  49: [38.74, 41.49], // Mus
  50: [38.63, 34.72], // Nevsehir
  51: [37.97, 34.68], // Nigde
  52: [40.98, 37.88], // Ordu
  53: [41.02, 40.52], // Rize
  54: [40.78, 30.40], // Sakarya
  55: [41.29, 36.33], // Samsun
  56: [37.93, 41.94], // Siirt
  57: [42.03, 35.15], // Sinop
  58: [39.75, 37.02], // Sivas
  59: [40.98, 27.51], // Tekirdag
  60: [40.32, 36.55], // Tokat
  61: [41.00, 39.72], // Trabzon
  62: [39.11, 39.55], // Tunceli
  63: [37.17, 38.80], // Sanliurfa
  64: [38.68, 29.40], // Usak
  65: [38.49, 43.38], // Van
  66: [39.82, 34.81], // Yozgat
  67: [41.45, 31.79], // Zonguldak
  68: [38.37, 34.03], // Aksaray
  69: [40.26, 40.22], // Bayburt
  70: [37.18, 33.22], // Karaman
  71: [39.84, 33.52], // Kirikkale
  72: [37.88, 41.14], // Batman
  73: [37.52, 42.45], // Sirnak
  74: [41.64, 32.34], // Bartin
  75: [41.11, 42.70], // Ardahan
  76: [39.92, 44.04], // Igdir
  77: [40.65, 29.27], // Yalova
  78: [41.20, 32.62], // Karabuk
  79: [36.72, 37.12], // Kilis
  80: [37.07, 36.24], // Osmaniye
  81: [40.84, 31.16], // Duzce
};

// Colors used by map legend and markers
export const ALERT_LEVEL_COLORS: Record<string, string> = {
  none: '#10b981',
  low: '#fbbf24',
  moderate: '#f59e0b',
  high: '#ef4444',
  extreme: '#991b1b',
};


