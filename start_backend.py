#!/usr/bin/env python3
"""
Backend başlatma script'i
"""
import os
import uvicorn

# PostgreSQL URL'yi ayarla
os.environ['DATABASE_URL'] = 'postgresql://postgres:123@localhost:5432/cosmicsparks_db'

print("🚀 CosmicSparks Backend başlatılıyor...")
print("🗄️ Database: cosmicsparks_db")
print("🌐 API: http://localhost:8000")
print("📖 Docs: http://localhost:8000/docs")
print("=" * 50)

# API'yi başlat
if __name__ == "__main__":
    uvicorn.run(
        "src.api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["src"]
    )
