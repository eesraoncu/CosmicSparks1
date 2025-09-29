# Türkiye Toz İzleme Sistemi - Deployment Rehberi

## 🚀 Hızlı Başlangıç

### 1. Sistem Gereksinimleri
- **Docker & Docker Compose** (Önerilen)
- **Python 3.10+** (Geliştirme için)
- **Node.js 18+** (Frontend geliştirme için)
- **PostgreSQL 15+** (Manuel kurulum için)

### 2. Otomatik Kurulum
```bash
# Repository'yi klonlayın
git clone <repository-url>
cd dust-mvp

# Kurulum script'ini çalıştırın
bash scripts/setup.sh

# Environment dosyasını düzenleyin
nano .env

# Sistemi başlatın
docker-compose up -d
```

### 3. Servis URL'leri
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

## 📋 Detaylı Kurulum

### Environment Konfigürasyonu (.env)
```bash
# NASA API Anahtarları
LAADS_TOKEN=your_nasa_laads_token_here
CAMS_API_KEY=your_copernicus_cams_key_here

# Veritabanı
DATABASE_URL=postgresql://dust_user:dust_password@localhost:5432/dust_mvp

# Email Servisi
SMTP_SERVER=smtp.gmail.com
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
FROM_EMAIL=noreply@dustalert.tr

# Uygulama URL'leri
WEBSITE_URL=http://localhost:3000
API_URL=http://localhost:8000
```

### API Anahtarları Alma

#### NASA LAADS Token
1. https://ladsweb.modaps.eosdis.nasa.gov/ adresine gidin
2. Ücretsiz hesap oluşturun
3. Profile → App Keys bölümünden token alın

#### ECMWF CAMS API Key
1. https://ads.atmosphere.copernicus.eu/ adresine gidin
2. Hesap oluşturun
3. API key'inizi alın

### Email Servisi Kurulumu

#### Gmail SMTP (Önerilen)
1. Gmail hesabınızda 2FA'yı etkinleştirin
2. App Password oluşturun
3. SMTP ayarları:
   - Server: smtp.gmail.com
   - Port: 587
   - Username: your_email@gmail.com
   - Password: your_app_password

## 🐳 Docker Deployment

### Production Deployment
```bash
# Production environment
export ENV=production

# SSL sertifikaları için
mkdir -p nginx/ssl
# SSL sertifikalarınızı nginx/ssl/ klasörüne koyun

# Production ile başlatma
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Servis Kontrolü
```bash
# Tüm servislerin durumunu kontrol edin
docker-compose ps

# Logları görüntüleyin
docker-compose logs -f

# Belirli bir servisin loglarını görüntüleyin
docker-compose logs -f api
docker-compose logs -f scheduler
docker-compose logs -f frontend
```

### Monitoring
```bash
# Health check'leri
curl http://localhost:8000/health
curl http://localhost:8000/api/system/status

# Sistem logları
docker-compose logs scheduler
```

## ⚙️ Manual Deployment

### Backend API
```bash
# Dependency'leri yükleyin
pip install -r requirements.txt

# Veritabanını initialize edin
python -c "from src.database import init_database; init_database()"

# API'yi başlatın
python -m uvicorn src.api:app --host 0.0.0.0 --port 8000
```

### Scheduler
```bash
# Scheduler'ı başlatın
python -m src.scheduler --daemon

# Tek seferlik çalıştırma
python -m src.scheduler --run-once 2025-09-29

# Alert işleme
python -m src.scheduler --process-alerts
```

### Frontend
```bash
cd frontend

# Dependency'leri yükleyin
npm install

# Development server
npm run dev

# Production build
npm run build
npm start
```

## 🔧 Konfigürasyon

### Pipeline Scheduler Ayarları
```yaml
# config/params.yaml
scheduler:
  daily_run_time: "06:00"  # UTC time
  pipeline_timeout_minutes: 60
  max_retries: 3
  retry_delay_minutes: 15
  alert_processing_interval_minutes: 10
  cleanup_old_data_days: 90
```

### Email Template Özelleştirme
```python
# src/email_service.py dosyasında template'leri düzenleyebilirsiniz
```

### Database Migration
```bash
# Yeni migration oluşturma
python -c "from src.database import Base, db_manager; db_manager.create_tables()"

# Veri backup
docker-compose exec postgres pg_dump -U dust_user dust_mvp > backup.sql

# Veri restore
docker-compose exec -T postgres psql -U dust_user dust_mvp < backup.sql
```

## 🚦 Production Checklist

### Güvenlik
- [ ] SSL sertifikaları yapılandırıldı
- [ ] Database şifreleri değiştirildi
- [ ] API rate limiting etkin
- [ ] CORS origins doğru yapılandırıldı
- [ ] Environment variables güvende

### Performance
- [ ] Redis caching etkin
- [ ] Database index'leri optimize edildi
- [ ] Nginx gzip compression etkin
- [ ] Static file caching yapılandırıldı

### Monitoring
- [ ] Health check endpoints çalışıyor
- [ ] Log aggregation kuruldu
- [ ] Alert monitoring yapılandırıldı
- [ ] Backup stratejisi planlandı

### Data Pipeline
- [ ] API keys test edildi
- [ ] Scheduler çalışıyor
- [ ] Email delivery test edildi
- [ ] Data quality monitoring etkin

## 🔍 Troubleshooting

### Yaygın Problemler

#### API Bağlantı Hatası
```bash
# Container'lar çalışıyor mu?
docker-compose ps

# Network bağlantısı
docker-compose exec api curl http://postgres:5432

# Health check
curl http://localhost:8000/health
```

#### Email Gönderim Hatası
```bash
# SMTP ayarlarını test edin
python -c "
from src.email_service import EmailService
service = EmailService()
print('SMTP Config:', service.smtp_config)
"
```

#### Database Bağlantı Hatası
```bash
# PostgreSQL durumu
docker-compose exec postgres pg_isready -U dust_user

# Database bağlantı testi
python -c "
from src.database import db_manager
with db_manager.get_session() as session:
    print('Database connection OK')
"
```

#### Frontend Build Hatası
```bash
cd frontend

# Cache temizleme
rm -rf .next node_modules
npm install
npm run build
```

### Log Analizi
```bash
# API error logs
docker-compose logs api | grep ERROR

# Scheduler execution logs
docker-compose logs scheduler | grep "Pipeline"

# Database query logs
docker-compose logs postgres | grep STATEMENT
```

## 📊 Performance Tuning

### Database Optimization
```sql
-- Index optimization
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_daily_stats_date_province 
ON daily_stats(date, province_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_alerts_user_created 
ON alerts(user_id, created_at);

-- Analyze tables
ANALYZE daily_stats;
ANALYZE alerts;
ANALYZE users;
```

### Redis Caching
```python
# API response caching (implement in src/api.py)
import redis
redis_client = redis.Redis(host='redis', port=6379, db=0)

# Cache daily stats for 1 hour
@cache(expire=3600)
def get_current_stats():
    # Implementation
    pass
```

### Nginx Optimization
```nginx
# nginx/nginx.conf optimization
gzip on;
gzip_types text/plain text/css application/json application/javascript;

# Static file caching
location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

## 🔄 Backup & Recovery

### Automated Backup Script
```bash
#!/bin/bash
# scripts/backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups"

# Database backup
docker-compose exec postgres pg_dump -U dust_user dust_mvp > "$BACKUP_DIR/db_$DATE.sql"

# Data files backup
tar -czf "$BACKUP_DIR/data_$DATE.tar.gz" data/

# Config backup
tar -czf "$BACKUP_DIR/config_$DATE.tar.gz" config/ .env

echo "Backup completed: $DATE"
```

### Recovery Procedure
```bash
# Stop services
docker-compose down

# Restore database
docker-compose up -d postgres
sleep 10
docker-compose exec -T postgres psql -U dust_user dust_mvp < backup.sql

# Restore data files
tar -xzf data_backup.tar.gz

# Start all services
docker-compose up -d
```

## 🌐 Production Domain Setup

### DNS Configuration
```
A record: dustalert.tr → your_server_ip
CNAME: www.dustalert.tr → dustalert.tr
CNAME: api.dustalert.tr → dustalert.tr
```

### SSL Setup (Let's Encrypt)
```bash
# Install certbot
sudo apt install certbot

# Get certificates
certbot certonly --standalone -d dustalert.tr -d www.dustalert.tr -d api.dustalert.tr

# Copy to nginx directory
cp /etc/letsencrypt/live/dustalert.tr/* nginx/ssl/

# Update docker-compose with SSL config
docker-compose restart nginx
```

Bu deployment rehberi sayesinde sistemi hem development hem de production ortamında başarıyla çalıştırabilirsiniz.
