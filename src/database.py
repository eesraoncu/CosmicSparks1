"""
Database models and connection management for Dust MVP
Handles user profiles, alerts, and data storage
"""
import os
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import String
import uuid

# Database configuration
Base = declarative_base()

class User(Base):
    """User profiles and preferences"""
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # User preferences
    health_group = Column(String(50), default='general')  # general, sensitive, respiratory, cardiac
    province_ids = Column(JSON)  # List of province IDs to monitor
    
    # Alert thresholds (PM2.5 μg/m³)
    pm25_low_threshold = Column(Float, default=25.0)
    pm25_moderate_threshold = Column(Float, default=50.0)
    pm25_high_threshold = Column(Float, default=75.0)
    dust_aod_threshold = Column(Float, default=0.15)
    
    # Notification preferences
    notify_forecast = Column(Boolean, default=True)
    notify_current = Column(Boolean, default=True)
    quiet_hours_start = Column(Integer, default=22)  # 22:00
    quiet_hours_end = Column(Integer, default=7)     # 07:00
    max_alerts_per_day = Column(Integer, default=3)
    
    # Subscription status
    is_active = Column(Boolean, default=True)
    email_verified = Column(Boolean, default=False)
    verification_token = Column(String(255))
    
    # Alert history tracking
    last_alert_time = Column(DateTime)
    daily_alert_count = Column(Integer, default=0)
    last_alert_date = Column(String(10))  # YYYY-MM-DD


class Province(Base):
    """Turkish provinces for reference"""
    __tablename__ = "provinces"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    name_en = Column(String(100))
    region = Column(String(50))
    population = Column(Integer)
    area_km2 = Column(Float)


class DailyStats(Base):
    """Daily province-level statistics"""
    __tablename__ = "daily_stats"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    date = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    province_id = Column(Integer, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # AOD statistics
    aod_mean = Column(Float)
    aod_max = Column(Float) 
    aod_p95 = Column(Float)
    aod_coverage_pct = Column(Float)
    
    # Dust statistics
    dust_aod_mean = Column(Float)
    dust_event_detected = Column(Boolean, default=False)
    dust_intensity = Column(String(20))  # None, Light, Moderate, Heavy, Extreme
    
    # PM2.5 estimates
    pm25 = Column(Float)
    pm25_lower = Column(Float)  # Lower confidence bound
    pm25_upper = Column(Float)  # Upper confidence bound
    air_quality_category = Column(String(50))  # Good, Moderate, Unhealthy for Sensitive Groups, etc.
    
    # Meteorological data
    rh_mean = Column(Float)  # Relative humidity %
    blh_mean = Column(Float)  # Boundary layer height (m)
    
    # Quality indicators
    data_quality_score = Column(Float)  # 0-1 score
    model_uncertainty = Column(Float)


class Alert(Base):
    """Alert queue and history"""
    __tablename__ = "alerts"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=False, index=True)
    province_id = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Alert details
    alert_level = Column(String(20), nullable=False)  # none, low, moderate, high, extreme
    pm25_value = Column(Float, nullable=False)
    pm25_threshold = Column(Float, nullable=False)
    
    # Dust context
    dust_detected = Column(Boolean, default=False)
    dust_intensity = Column(String(20))
    
    # Message content
    health_message = Column(Text)
    forecast_hours = Column(Integer, default=0)  # 0 = current, >0 = forecast
    
    # Delivery status
    email_sent = Column(Boolean, default=False)
    email_sent_at = Column(DateTime)
    email_error = Column(Text)
    
    # Additional context
    alert_metadata = Column(JSON)  # Additional context data


class SystemStatus(Base):
    """System monitoring and pipeline status"""
    __tablename__ = "system_status"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    date = Column(String(10), nullable=False, index=True)
    component = Column(String(50), nullable=False)  # modis, cams, era5, pipeline
    status = Column(String(20), nullable=False)  # success, warning, error
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Status details
    message = Column(Text)
    processing_time_seconds = Column(Float)
    data_coverage_pct = Column(Float)
    
    # Error tracking
    error_details = Column(JSON)


class DatabaseManager:
    """Database connection and operations management"""
    
    def __init__(self, database_url: str = None):
        if database_url is None:
            # Default to local SQLite for development
            database_url = "postgresql://postgres:123@localhost:5432/cosmicsparks_db"
        
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
    def create_tables(self):
        """Create all database tables"""
        Base.metadata.create_all(bind=self.engine)
        
    def get_session(self) -> Session:
        """Get database session"""
        return self.SessionLocal()
    
    def insert_provinces(self, session: Session):
        """Insert Turkish provinces data"""
        provinces_data = [
            # Türkiye'nin 81 ili - 2023 nüfus verilerine göre
            {"id": 1, "name": "Adana", "name_en": "Adana", "region": "Akdeniz", "population": 2274106, "area_km2": 13844},
            {"id": 2, "name": "Adıyaman", "name_en": "Adiyaman", "region": "Güneydoğu Anadolu", "population": 635169, "area_km2": 7614},
            {"id": 3, "name": "Afyonkarahisar", "name_en": "Afyonkarahisar", "region": "Ege", "population": 747555, "area_km2": 14532},
            {"id": 4, "name": "Ağrı", "name_en": "Agri", "region": "Doğu Anadolu", "population": 535435, "area_km2": 11376},
            {"id": 5, "name": "Amasya", "name_en": "Amasya", "region": "Karadeniz", "population": 335494, "area_km2": 5628},
            {"id": 6, "name": "Ankara", "name_en": "Ankara", "region": "İç Anadolu", "population": 5747325, "area_km2": 25632},
            {"id": 7, "name": "Antalya", "name_en": "Antalya", "region": "Akdeniz", "population": 2619832, "area_km2": 20177},
            {"id": 8, "name": "Artvin", "name_en": "Artvin", "region": "Karadeniz", "population": 170875, "area_km2": 7393},
            {"id": 9, "name": "Aydın", "name_en": "Aydin", "region": "Ege", "population": 1148241, "area_km2": 8116},
            {"id": 10, "name": "Balıkesir", "name_en": "Balikesir", "region": "Marmara", "population": 1257590, "area_km2": 14583},
            {"id": 11, "name": "Bilecik", "name_en": "Bilecik", "region": "Marmara", "population": 228673, "area_km2": 4179},
            {"id": 12, "name": "Bingöl", "name_en": "Bingol", "region": "Doğu Anadolu", "population": 282556, "area_km2": 8004},
            {"id": 13, "name": "Bitlis", "name_en": "Bitlis", "region": "Doğu Anadolu", "population": 353988, "area_km2": 6707},
            {"id": 14, "name": "Bolu", "name_en": "Bolu", "region": "Karadeniz", "population": 320824, "area_km2": 8313},
            {"id": 15, "name": "Burdur", "name_en": "Burdur", "region": "Akdeniz", "population": 273799, "area_km2": 6887},
            {"id": 16, "name": "Bursa", "name_en": "Bursa", "region": "Marmara", "population": 3139744, "area_km2": 10813},
            {"id": 17, "name": "Çanakkale", "name_en": "Canakkale", "region": "Marmara", "population": 557061, "area_km2": 9817},
            {"id": 18, "name": "Çankırı", "name_en": "Cankiri", "region": "İç Anadolu", "population": 195789, "area_km2": 7388},
            {"id": 19, "name": "Çorum", "name_en": "Corum", "region": "Karadeniz", "population": 530126, "area_km2": 12428},
            {"id": 20, "name": "Denizli", "name_en": "Denizli", "region": "Ege", "population": 1037208, "area_km2": 12134},
            {"id": 21, "name": "Diyarbakır", "name_en": "Diyarbakir", "region": "Güneydoğu Anadolu", "population": 1804880, "area_km2": 15355},
            {"id": 22, "name": "Edirne", "name_en": "Edirne", "region": "Marmara", "population": 413903, "area_km2": 6145},
            {"id": 23, "name": "Elazığ", "name_en": "Elazig", "region": "Doğu Anadolu", "population": 591098, "area_km2": 9383},
            {"id": 24, "name": "Erzincan", "name_en": "Erzincan", "region": "Doğu Anadolu", "population": 236034, "area_km2": 11815},
            {"id": 25, "name": "Erzurum", "name_en": "Erzurum", "region": "Doğu Anadolu", "population": 762321, "area_km2": 25066},
            {"id": 26, "name": "Eskişehir", "name_en": "Eskisehir", "region": "İç Anadolu", "population": 898369, "area_km2": 13960},
            {"id": 27, "name": "Gaziantep", "name_en": "Gaziantep", "region": "Güneydoğu Anadolu", "population": 2130432, "area_km2": 6222},
            {"id": 28, "name": "Giresun", "name_en": "Giresun", "region": "Karadeniz", "population": 452912, "area_km2": 6934},
            {"id": 29, "name": "Gümüşhane", "name_en": "Gumushane", "region": "Karadeniz", "population": 151449, "area_km2": 6575},
            {"id": 30, "name": "Hakkâri", "name_en": "Hakkari", "region": "Doğu Anadolu", "population": 287727, "area_km2": 7121},
            {"id": 31, "name": "Hatay", "name_en": "Hatay", "region": "Akdeniz", "population": 1659320, "area_km2": 5524},
            {"id": 32, "name": "Isparta", "name_en": "Isparta", "region": "Akdeniz", "population": 442249, "area_km2": 8993},
            {"id": 33, "name": "Mersin", "name_en": "Mersin", "region": "Akdeniz", "population": 1916432, "area_km2": 16010},
            {"id": 34, "name": "İstanbul", "name_en": "Istanbul", "region": "Marmara", "population": 15840900, "area_km2": 5343},
            {"id": 35, "name": "İzmir", "name_en": "Izmir", "region": "Ege", "population": 4394694, "area_km2": 11973},
            {"id": 36, "name": "Kars", "name_en": "Kars", "region": "Doğu Anadolu", "population": 285410, "area_km2": 9587},
            {"id": 37, "name": "Kastamonu", "name_en": "Kastamonu", "region": "Karadeniz", "population": 383373, "area_km2": 13064},
            {"id": 38, "name": "Kayseri", "name_en": "Kayseri", "region": "İç Anadolu", "population": 1421362, "area_km2": 16917},
            {"id": 39, "name": "Kırklareli", "name_en": "Kirklareli", "region": "Marmara", "population": 373532, "area_km2": 6459},
            {"id": 40, "name": "Kırşehir", "name_en": "Kirsehir", "region": "İç Anadolu", "population": 253846, "area_km2": 6584},
            {"id": 41, "name": "Kocaeli", "name_en": "Kocaeli", "region": "Marmara", "population": 2033441, "area_km2": 3626},
            {"id": 42, "name": "Konya", "name_en": "Konya", "region": "İç Anadolu", "population": 2277017, "area_km2": 40838},
            {"id": 43, "name": "Kütahya", "name_en": "Kutahya", "region": "Ege", "population": 580701, "area_km2": 11634},
            {"id": 44, "name": "Malatya", "name_en": "Malatya", "region": "Doğu Anadolu", "population": 812580, "area_km2": 12259},
            {"id": 45, "name": "Manisa", "name_en": "Manisa", "region": "Ege", "population": 1468279, "area_km2": 13339},
            {"id": 46, "name": "Kahramanmaraş", "name_en": "Kahramanmaras", "region": "Akdeniz", "population": 1168163, "area_km2": 14520},
            {"id": 47, "name": "Mardin", "name_en": "Mardin", "region": "Güneydoğu Anadolu", "population": 854716, "area_km2": 8780},
            {"id": 48, "name": "Muğla", "name_en": "Mugla", "region": "Ege", "population": 1023492, "area_km2": 13338},
            {"id": 49, "name": "Muş", "name_en": "Mus", "region": "Doğu Anadolu", "population": 408809, "area_km2": 8196},
            {"id": 50, "name": "Nevşehir", "name_en": "Nevsehir", "region": "İç Anadolu", "population": 303010, "area_km2": 5485},
            {"id": 51, "name": "Niğde", "name_en": "Nigde", "region": "İç Anadolu", "population": 364707, "area_km2": 7312},
            {"id": 52, "name": "Ordu", "name_en": "Ordu", "region": "Karadeniz", "population": 771932, "area_km2": 6001},
            {"id": 53, "name": "Rize", "name_en": "Rize", "region": "Karadeniz", "population": 348608, "area_km2": 3920},
            {"id": 54, "name": "Sakarya", "name_en": "Sakarya", "region": "Marmara", "population": 1042649, "area_km2": 4824},
            {"id": 55, "name": "Samsun", "name_en": "Samsun", "region": "Karadeniz", "population": 1348542, "area_km2": 9725},
            {"id": 56, "name": "Siirt", "name_en": "Siirt", "region": "Güneydoğu Anadolu", "population": 331670, "area_km2": 5406},
            {"id": 57, "name": "Sinop", "name_en": "Sinop", "region": "Karadeniz", "population": 220799, "area_km2": 5862},
            {"id": 58, "name": "Sivas", "name_en": "Sivas", "region": "İç Anadolu", "population": 646608, "area_km2": 28488},
            {"id": 59, "name": "Tekirdağ", "name_en": "Tekirdag", "region": "Marmara", "population": 1081065, "area_km2": 6218},
            {"id": 60, "name": "Tokat", "name_en": "Tokat", "region": "Karadeniz", "population": 596454, "area_km2": 9958},
            {"id": 61, "name": "Trabzon", "name_en": "Trabzon", "region": "Karadeniz", "population": 811901, "area_km2": 4628},
            {"id": 62, "name": "Tunceli", "name_en": "Tunceli", "region": "Doğu Anadolu", "population": 84022, "area_km2": 7774},
            {"id": 63, "name": "Şanlıurfa", "name_en": "Sanliurfa", "region": "Güneydoğu Anadolu", "population": 2073614, "area_km2": 18584},
            {"id": 64, "name": "Uşak", "name_en": "Usak", "region": "Ege", "population": 371509, "area_km2": 5341},
            {"id": 65, "name": "Van", "name_en": "Van", "region": "Doğu Anadolu", "population": 1149342, "area_km2": 19069},
            {"id": 66, "name": "Yozgat", "name_en": "Yozgat", "region": "İç Anadolu", "population": 421766, "area_km2": 14123},
            {"id": 67, "name": "Zonguldak", "name_en": "Zonguldak", "region": "Karadeniz", "population": 588495, "area_km2": 3342},
            {"id": 68, "name": "Aksaray", "name_en": "Aksaray", "region": "İç Anadolu", "population": 433055, "area_km2": 7626},
            {"id": 69, "name": "Bayburt", "name_en": "Bayburt", "region": "Karadeniz", "population": 84843, "area_km2": 3652},
            {"id": 70, "name": "Karaman", "name_en": "Karaman", "region": "İç Anadolu", "population": 259864, "area_km2": 8678},
            {"id": 71, "name": "Kırıkkale", "name_en": "Kirikkale", "region": "İç Anadolu", "population": 280234, "area_km2": 4365},
            {"id": 72, "name": "Batman", "name_en": "Batman", "region": "Güneydoğu Anadolu", "population": 620278, "area_km2": 4477},
            {"id": 73, "name": "Şırnak", "name_en": "Sirnak", "region": "Güneydoğu Anadolu", "population": 537762, "area_km2": 7078},
            {"id": 74, "name": "Bartın", "name_en": "Bartin", "region": "Karadeniz", "population": 197509, "area_km2": 2330},
            {"id": 75, "name": "Ardahan", "name_en": "Ardahan", "region": "Doğu Anadolu", "population": 95326, "area_km2": 5661},
            {"id": 76, "name": "Iğdır", "name_en": "Igdir", "region": "Doğu Anadolu", "population": 203594, "area_km2": 3664},
            {"id": 77, "name": "Yalova", "name_en": "Yalova", "region": "Marmara", "population": 276050, "area_km2": 798},
            {"id": 78, "name": "Karabük", "name_en": "Karabuk", "region": "Karadeniz", "population": 248014, "area_km2": 4142},
            {"id": 79, "name": "Kilis", "name_en": "Kilis", "region": "Güneydoğu Anadolu", "population": 142490, "area_km2": 1412},
            {"id": 80, "name": "Osmaniye", "name_en": "Osmaniye", "region": "Akdeniz", "population": 559405, "area_km2": 3320},
            {"id": 81, "name": "Düzce", "name_en": "Duzce", "region": "Karadeniz", "population": 405140, "area_km2": 2492},
        ]
        
        for province_data in provinces_data:
            existing = session.query(Province).filter(Province.id == province_data["id"]).first()
            if not existing:
                province = Province(**province_data)
                session.add(province)
        
        session.commit()
    
    def store_daily_stats(self, session: Session, stats_data: List[Dict[str, Any]]):
        """Store daily province statistics"""
        for stat in stats_data:
            # Check if data already exists
            existing = session.query(DailyStats).filter(
                DailyStats.date == stat['date'],
                DailyStats.province_id == stat['province_id']
            ).first()
            
            if existing:
                # Update existing record
                for key, value in stat.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
            else:
                # Create new record
                daily_stat = DailyStats(**stat)
                session.add(daily_stat)
        
        session.commit()
    
    def get_user_by_email(self, session: Session, email: str) -> Optional[User]:
        """Get user by email"""
        return session.query(User).filter(User.email == email).first()
    
    def create_user(self, session: Session, user_data: Dict[str, Any]) -> User:
        """Create new user"""
        user = User(**user_data)
        user.verification_token = str(uuid.uuid4())
        session.add(user)
        session.commit()
        session.refresh(user)
        return user
    
    def queue_alert(self, session: Session, alert_data: Dict[str, Any]) -> Alert:
        """Queue alert for delivery"""
        alert = Alert(**alert_data)
        session.add(alert)
        session.commit()
        session.refresh(alert)
        return alert
    
    def get_pending_alerts(self, session: Session, limit: int = 100) -> List[Alert]:
        """Get pending alerts for email delivery"""
        return session.query(Alert).filter(Alert.email_sent == False).limit(limit).all()
    
    def mark_alert_sent(self, session: Session, alert_id: str, sent_at: datetime = None, error: str = None):
        """Mark alert as sent or failed"""
        alert = session.query(Alert).filter(Alert.id == alert_id).first()
        if alert:
            alert.email_sent = (error is None)
            alert.email_sent_at = sent_at or datetime.utcnow()
            if error:
                alert.email_error = error
            session.commit()
    
    def get_latest_stats(self, session: Session, province_ids: List[int] = None, 
                        days: int = 7) -> List[DailyStats]:
        """Get latest statistics for provinces"""
        query = session.query(DailyStats)
        
        if province_ids:
            query = query.filter(DailyStats.province_id.in_(province_ids))
        
        # Get last N days
        start_date = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%d')
        query = query.filter(DailyStats.date >= start_date)
        
        return query.order_by(DailyStats.date.desc(), DailyStats.province_id).all()


# Global database instance
db_manager = DatabaseManager()

def get_db() -> Session:
    """Dependency for FastAPI"""
    db = db_manager.get_session()
    try:
        yield db
    finally:
        db.close()


def init_database():
    """Initialize database with tables and basic data"""
    db_manager.create_tables()
    
    with db_manager.get_session() as session:
        db_manager.insert_provinces(session)
        print("Database initialized successfully")


if __name__ == "__main__":
    # Initialize database for testing
    init_database()
    
    # Test basic operations
    with db_manager.get_session() as session:
        # Test user creation
        user_data = {
            "email": "test@example.com",
            "health_group": "general",
            "province_ids": [1, 2]  # Istanbul, Ankara
        }
        
        user = db_manager.create_user(session, user_data)
        print(f"Created user: {user.email} (ID: {user.id})")
        
        # Test stats storage
        test_stats = [
            {
                "date": "2025-09-29",
                "province_id": 1,
                "aod_mean": 0.25,
                "dust_aod_mean": 0.05,
                "pm25": 35.2,
                "air_quality_category": "Moderate"
            }
        ]
        
        db_manager.store_daily_stats(session, test_stats)
        print("Stored test statistics")
        
        # Test alert queueing
        alert_data = {
            "user_id": user.id,
            "province_id": 1,
            "alert_level": "moderate",
            "pm25_value": 45.0,
            "pm25_threshold": 35.0,
            "health_message": "Air quality is unhealthy for sensitive groups"
        }
        
        alert = db_manager.queue_alert(session, alert_data)
        print(f"Queued alert: {alert.id}")
