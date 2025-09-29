#!/bin/bash

# Dust MVP Setup Script
echo "🌪️ Türkiye Toz İzleme Sistemi - Kurulum Başlıyor..."

# Create necessary directories
echo "📁 Dizinler oluşturuluyor..."
mkdir -p data/raw/{modis,cams,era5,aeronet}
mkdir -p data/derived
mkdir -p data/admin
mkdir -p logs
mkdir -p nginx/ssl

# Copy environment template
if [ ! -f .env ]; then
    echo "⚙️ Environment dosyası oluşturuluyor..."
    cat > .env << EOF
# API Keys
LAADS_TOKEN=your_nasa_laads_token_here
CAMS_API_KEY=your_copernicus_cams_key_here

# Database
DATABASE_URL=postgresql://dust_user:dust_password@localhost:5432/dust_mvp

# Email Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
FROM_EMAIL=noreply@dustalert.tr

# Application URLs
WEBSITE_URL=http://localhost:3000
API_URL=http://localhost:8000

# Optional: Redis for caching
REDIS_URL=redis://localhost:6379
EOF
    echo "✅ .env dosyası oluşturuldu. Lütfen API anahtarlarınızı ekleyin!"
else
    echo "⚠️ .env dosyası zaten mevcut."
fi

# Create nginx configuration
echo "🌐 Nginx konfigürasyonu oluşturuluyor..."
mkdir -p nginx
cat > nginx/nginx.conf << EOF
events {
    worker_connections 1024;
}

http {
    upstream api {
        server api:8000;
    }
    
    upstream frontend {
        server frontend:3000;
    }
    
    server {
        listen 80;
        server_name localhost;
        
        # Frontend
        location / {
            proxy_pass http://frontend;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
        }
        
        # API
        location /api/ {
            proxy_pass http://api;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
        }
        
        # Health check
        location /health {
            proxy_pass http://api;
        }
    }
}
EOF

# Create database initialization script
echo "🗄️ Veritabanı initialization script'i oluşturuluyor..."
cat > scripts/init-db.sql << EOF
-- Create extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create database user if not exists
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'dust_user') THEN
        CREATE ROLE dust_user LOGIN PASSWORD 'dust_password';
    END IF;
END
\$\$;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE dust_mvp TO dust_user;
GRANT ALL ON SCHEMA public TO dust_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO dust_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO dust_user;

-- Create basic tables will be handled by the application
EOF

# Check for required tools
echo "🔧 Gerekli araçlar kontrol ediliyor..."

if ! command -v docker &> /dev/null; then
    echo "❌ Docker bulunamadı. Lütfen Docker'ı yükleyin: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose bulunamadı. Lütfen Docker Compose'u yükleyin."
    exit 1
fi

# Install Python dependencies (for local development)
if command -v python3 &> /dev/null; then
    echo "🐍 Python dependency'leri yükleniyor..."
    python3 -m pip install -r requirements.txt
else
    echo "⚠️ Python3 bulunamadı. Local development için Python3 gereklidir."
fi

# Install Node.js dependencies (for frontend development)
if command -v npm &> /dev/null; then
    echo "📦 Frontend dependency'leri yükleniyor..."
    cd frontend
    npm install
    cd ..
else
    echo "⚠️ npm bulunamadı. Frontend development için Node.js gereklidir."
fi

echo "✅ Kurulum tamamlandı!"
echo ""
echo "🚀 Sistemi başlatmak için:"
echo "   docker-compose up -d"
echo ""
echo "📋 Servisler:"
echo "   - Frontend: http://localhost:3000"
echo "   - API: http://localhost:8000"
echo "   - PostgreSQL: localhost:5432"
echo "   - Redis: localhost:6379"
echo ""
echo "⚙️ Lütfen .env dosyasını düzenleyerek API anahtarlarınızı ekleyin:"
echo "   - NASA LAADS Token"
echo "   - ECMWF CAMS API Key"
echo "   - SMTP Email ayarları"
echo ""
echo "📚 Dokümantasyon: docs/readme.txt"
echo "🧪 Test: python test_pipeline.py"
