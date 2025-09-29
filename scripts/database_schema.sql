-- Türkiye Toz İzleme Sistemi - Veritabanı Şeması
-- PostgreSQL + PostGIS tabloları

-- Extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Kullanıcı tablosu - Alert subscription ve preferences
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- User preferences
    health_group VARCHAR(50) DEFAULT 'general', -- general, sensitive, respiratory, cardiac
    province_ids JSON, -- List of province IDs to monitor
    
    -- Alert thresholds (PM2.5 μg/m³)
    pm25_low_threshold FLOAT DEFAULT 25.0,
    pm25_moderate_threshold FLOAT DEFAULT 50.0,
    pm25_high_threshold FLOAT DEFAULT 75.0,
    dust_aod_threshold FLOAT DEFAULT 0.15,
    
    -- Notification preferences
    notify_forecast BOOLEAN DEFAULT TRUE,
    notify_current BOOLEAN DEFAULT TRUE,
    quiet_hours_start INTEGER DEFAULT 22, -- 22:00
    quiet_hours_end INTEGER DEFAULT 7,    -- 07:00
    max_alerts_per_day INTEGER DEFAULT 3,
    
    -- Subscription status
    is_active BOOLEAN DEFAULT TRUE,
    email_verified BOOLEAN DEFAULT FALSE,
    verification_token VARCHAR(255),
    
    -- Alert history tracking
    last_alert_time TIMESTAMP,
    daily_alert_count INTEGER DEFAULT 0,
    last_alert_date VARCHAR(10) -- YYYY-MM-DD
);

-- İller referans tablosu
CREATE TABLE provinces (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    name_en VARCHAR(100),
    region VARCHAR(50),
    population INTEGER,
    area_km2 FLOAT
);

-- Günlük il bazında istatistikler
CREATE TABLE daily_stats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date VARCHAR(10) NOT NULL, -- YYYY-MM-DD
    province_id INTEGER NOT NULL REFERENCES provinces(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- AOD statistics
    aod_mean FLOAT,
    aod_max FLOAT,
    aod_p95 FLOAT,
    aod_coverage_pct FLOAT,
    
    -- Dust statistics
    dust_aod_mean FLOAT,
    dust_event_detected BOOLEAN DEFAULT FALSE,
    dust_intensity VARCHAR(20), -- None, Light, Moderate, Heavy, Extreme
    
    -- PM2.5 estimates
    pm25 FLOAT,
    pm25_lower FLOAT, -- Lower confidence bound
    pm25_upper FLOAT, -- Upper confidence bound
    air_quality_category VARCHAR(20), -- Good, Moderate, Unhealthy, etc.
    
    -- Meteorological data
    rh_mean FLOAT, -- Relative humidity %
    blh_mean FLOAT, -- Boundary layer height (m)
    
    -- Quality indicators
    data_quality_score FLOAT, -- 0-1 score
    model_uncertainty FLOAT
);

-- Alert queue ve history
CREATE TABLE alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id),
    province_id INTEGER NOT NULL REFERENCES provinces(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Alert details
    alert_level VARCHAR(20) NOT NULL, -- none, low, moderate, high, extreme
    pm25_value FLOAT NOT NULL,
    pm25_threshold FLOAT NOT NULL,
    
    -- Dust context
    dust_detected BOOLEAN DEFAULT FALSE,
    dust_intensity VARCHAR(20),
    
    -- Message content
    health_message TEXT,
    forecast_hours INTEGER DEFAULT 0, -- 0 = current, >0 = forecast
    
    -- Delivery status
    email_sent BOOLEAN DEFAULT FALSE,
    email_sent_at TIMESTAMP,
    email_error TEXT,
    
    -- Additional context
    metadata JSON
);

-- Sistem monitoring tablosu
CREATE TABLE system_status (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date VARCHAR(10) NOT NULL, -- YYYY-MM-DD
    component VARCHAR(50) NOT NULL, -- modis, cams, era5, pipeline
    status VARCHAR(20) NOT NULL, -- success, warning, error
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Status details
    message TEXT,
    processing_time_seconds FLOAT,
    data_coverage_pct FLOAT,
    
    -- Error tracking
    error_details JSON
);

-- Indexes for performance
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_active ON users(is_active) WHERE is_active = TRUE;

CREATE INDEX idx_daily_stats_date ON daily_stats(date);
CREATE INDEX idx_daily_stats_province ON daily_stats(province_id);
CREATE INDEX idx_daily_stats_date_province ON daily_stats(date, province_id);

CREATE INDEX idx_alerts_user ON alerts(user_id);
CREATE INDEX idx_alerts_created ON alerts(created_at);
CREATE INDEX idx_alerts_user_created ON alerts(user_id, created_at);
CREATE INDEX idx_alerts_pending ON alerts(email_sent) WHERE email_sent = FALSE;

CREATE INDEX idx_system_status_date ON system_status(date);
CREATE INDEX idx_system_status_component ON system_status(component);

-- Trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- İllerin başlangıç verileri
INSERT INTO provinces (id, name, name_en, region, population, area_km2) VALUES
(1, 'İstanbul', 'Istanbul', 'Marmara', 15840900, 5343),
(2, 'Ankara', 'Ankara', 'İç Anadolu', 5747325, 25632),
(3, 'İzmir', 'Izmir', 'Ege', 4394694, 11973),
(4, 'Bursa', 'Bursa', 'Marmara', 3139744, 10813),
(5, 'Antalya', 'Antalya', 'Akdeniz', 2619832, 20177),
(6, 'Adana', 'Adana', 'Akdeniz', 2274106, 13844),
(7, 'Konya', 'Konya', 'İç Anadolu', 2277017, 40838),
(8, 'Şanlıurfa', 'Sanliurfa', 'Güneydoğu Anadolu', 2073614, 18584),
(9, 'Gaziantep', 'Gaziantep', 'Güneydoğu Anadolu', 2130432, 6222),
(10, 'Kocaeli', 'Kocaeli', 'Marmara', 2033441, 3626),
(11, 'Mersin', 'Mersin', 'Akdeniz', 1868757, 15853),
(12, 'Kayseri', 'Kayseri', 'İç Anadolu', 1421362, 16917),
(13, 'Eskişehir', 'Eskisehir', 'İç Anadolu', 888828, 13652),
(14, 'Diyarbakır', 'Diyarbakir', 'Güneydoğu Anadolu', 1783431, 15355),
(15, 'Samsun', 'Samsun', 'Karadeniz', 1370366, 9725),
(16, 'Denizli', 'Denizli', 'Ege', 1037208, 11868),
(17, 'Şahinbey', 'Sahinbey', 'Güneydoğu Anadolu', 1000000, 1300), -- Gaziantep'in merkez ilçesi
(18, 'Adapazarı', 'Adapazari', 'Marmara', 295400, 324),
(19, 'Malatya', 'Malatya', 'Doğu Anadolu', 797036, 12259),
(20, 'Kahramanmaraş', 'Kahramanmaras', 'Akdeniz', 1168163, 14520),
-- Diğer önemli iller...
(34, 'İstanbul', 'Istanbul', 'Marmara', 15840900, 5343), -- Plaka kodu ile
(35, 'İzmir', 'Izmir', 'Ege', 4394694, 11973),
(41, 'Kocaeli', 'Kocaeli', 'Marmara', 2033441, 3626),
(42, 'Konya', 'Konya', 'İç Anadolu', 2277017, 40838),
(54, 'Sakarya', 'Sakarya', 'Marmara', 1042649, 4824),
(61, 'Trabzon', 'Trabzon', 'Karadeniz', 811901, 4685),
(63, 'Şanlıurfa', 'Sanliurfa', 'Güneydoğu Anadolu', 2073614, 18584);

-- Örnek test kullanıcısı
INSERT INTO users (email, health_group, province_ids, pm25_moderate_threshold) VALUES
('test@dustalert.tr', 'general', '[1, 2, 6]', 50.0);

-- Güvenlik ve permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO dust_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO dust_user;

-- View'lar (Kolay sorgular için)
CREATE VIEW latest_province_stats AS
SELECT DISTINCT ON (province_id) 
    daily_stats.*,
    provinces.name as province_name,
    provinces.region
FROM daily_stats 
JOIN provinces ON daily_stats.province_id = provinces.id
ORDER BY province_id, date DESC;

CREATE VIEW alert_summary AS
SELECT 
    date,
    COUNT(*) as total_alerts,
    COUNT(*) FILTER (WHERE alert_level = 'high') as high_alerts,
    COUNT(*) FILTER (WHERE alert_level = 'extreme') as extreme_alerts,
    COUNT(*) FILTER (WHERE email_sent = true) as emails_sent
FROM alerts 
GROUP BY date
ORDER BY date DESC;
