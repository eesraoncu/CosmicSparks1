#!/usr/bin/env python3
"""
Hızlı veritabanı kurulum - Kullanıcı dostu versiyon
"""
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

def setup_database_url():
    """DATABASE_URL environment variable'ını ayarla"""
    database_url = "postgresql://dust_user:dust_password@localhost:5432/dust_mvp"
    os.environ['DATABASE_URL'] = database_url
    print(f"🔗 Database URL: {database_url}")

def quick_setup():
    """Hızlı kurulum - Var olan PostgreSQL'e bağlan"""
    try:
        from database import db_manager
        
        print("🌪️ Türkiye Toz İzleme Sistemi - Hızlı Veritabanı Kurulumu")
        print("=" * 60)
        
        # Database URL'yi ayarla
        setup_database_url()
        
        print("📋 Tabloları oluşturuyor...")
        db_manager.create_tables()
        
        print("🗺️ Türkiye illeri ekleniyor...")
        with db_manager.get_session() as session:
            db_manager.insert_provinces(session)
            
        print("👤 Test kullanıcısı oluşturuluyor...")
        with db_manager.get_session() as session:
            test_user = {
                "email": "test@dustalert.tr",
                "health_group": "general",
                "province_ids": [1, 2, 6]  # İstanbul, Ankara, Adana
            }
            user = db_manager.create_user(session, test_user)
            print(f"✅ Test kullanıcısı: {user.email}")
        
        print("\n🎉 Veritabanı kurulumu tamamlandı!")
        print("\n📋 Sonraki adımlar:")
        print("1. API başlat: python -m uvicorn src.api:app --reload")
        print("2. Frontend başlat: cd frontend && npm run dev")
        print("3. Test: http://localhost:8000/docs")
        
        return True
        
    except Exception as e:
        print(f"❌ Hata: {e}")
        print("\n💡 Çözüm önerileri:")
        print("1. PostgreSQL'in çalıştığından emin olun")
        print("2. Database connection string'i kontrol edin")
        print("3. Docker ile kurulum deneyin: docker-compose up -d")
        return False

if __name__ == "__main__":
    quick_setup()
