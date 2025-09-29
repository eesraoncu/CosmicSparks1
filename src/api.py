"""
REST API for Dust MVP system
Provides endpoints for data access, user management, and alert subscriptions
"""
import os
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
import pandas as pd

from .database import get_db, db_manager, User, Province, DailyStats, Alert
from .email_service import EmailService

# Pydantic models for API
class UserCreate(BaseModel):
    email: EmailStr
    health_group: str = Field(default="general", pattern="^(general|sensitive|respiratory|cardiac)$")
    province_ids: List[int] = Field(..., min_items=1, max_items=10)
    pm25_low_threshold: Optional[float] = Field(default=25.0, ge=0, le=500)
    pm25_moderate_threshold: Optional[float] = Field(default=50.0, ge=0, le=500)
    pm25_high_threshold: Optional[float] = Field(default=75.0, ge=0, le=500)
    dust_aod_threshold: Optional[float] = Field(default=0.15, ge=0, le=5)
    notify_forecast: bool = True
    notify_current: bool = True
    quiet_hours_start: int = Field(default=22, ge=0, le=23)
    quiet_hours_end: int = Field(default=7, ge=0, le=23)
    max_alerts_per_day: int = Field(default=3, ge=1, le=10)


class UserUpdate(BaseModel):
    health_group: Optional[str] = Field(None, pattern="^(general|sensitive|respiratory|cardiac)$")
    province_ids: Optional[List[int]] = Field(None, min_items=1, max_items=10)
    pm25_low_threshold: Optional[float] = Field(None, ge=0, le=500)
    pm25_moderate_threshold: Optional[float] = Field(None, ge=0, le=500) 
    pm25_high_threshold: Optional[float] = Field(None, ge=0, le=500)
    dust_aod_threshold: Optional[float] = Field(None, ge=0, le=5)
    notify_forecast: Optional[bool] = None
    notify_current: Optional[bool] = None
    quiet_hours_start: Optional[int] = Field(None, ge=0, le=23)
    quiet_hours_end: Optional[int] = Field(None, ge=0, le=23)
    max_alerts_per_day: Optional[int] = Field(None, ge=1, le=10)
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    id: str
    email: str
    health_group: str
    province_ids: List[int]
    pm25_low_threshold: float
    pm25_moderate_threshold: float
    pm25_high_threshold: float
    dust_aod_threshold: float
    notify_forecast: bool
    notify_current: bool
    quiet_hours_start: int
    quiet_hours_end: int
    max_alerts_per_day: int
    is_active: bool
    email_verified: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class ProvinceResponse(BaseModel):
    id: int
    name: str
    name_en: Optional[str]
    region: Optional[str]
    population: Optional[int]
    area_km2: Optional[float]
    
    class Config:
        from_attributes = True


class DailyStatsResponse(BaseModel):
    date: str
    province_id: int
    aod_mean: Optional[float]
    aod_max: Optional[float]
    aod_p95: Optional[float]
    dust_aod_mean: Optional[float]
    dust_event_detected: Optional[bool]
    dust_intensity: Optional[str]
    pm25: Optional[float]
    pm25_lower: Optional[float]
    pm25_upper: Optional[float]
    air_quality_category: Optional[str]
    rh_mean: Optional[float]
    blh_mean: Optional[float]
    data_quality_score: Optional[float]
    
    class Config:
        from_attributes = True


class AlertResponse(BaseModel):
    id: str
    province_id: int
    alert_level: str
    pm25_value: float
    dust_detected: bool
    dust_intensity: Optional[str]
    health_message: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# FastAPI app setup
app = FastAPI(
    title="Dust MVP API",
    description="API for Turkish dust monitoring and health alert system",
    version="1.0.0"
)

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Initialize email service
email_service = EmailService()


@app.on_event("startup")
async def startup_event():
    """Initialize database and services on startup"""
    db_manager.create_tables()
    
    # Insert basic province data
    with db_manager.get_session() as session:
        db_manager.insert_provinces(session)


# User management endpoints
@app.post("/api/users/", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Register new user for alerts"""
    # Check if user already exists
    existing_user = db_manager.get_user_by_email(db, user_data.email)
    if existing_user:
        if existing_user.email_verified:
            raise HTTPException(status_code=400, detail="User already exists and verified")
        else:
            # Resend verification email
            background_tasks.add_task(
                email_service.send_verification_email,
                existing_user.email,
                existing_user.verification_token
            )
            return existing_user
    
    # Validate province IDs
    valid_provinces = db.query(Province).filter(Province.id.in_(user_data.province_ids)).all()
    if len(valid_provinces) != len(user_data.province_ids):
        raise HTTPException(status_code=400, detail="Invalid province IDs")
    
    # Create user
    user = db_manager.create_user(db, user_data.dict())
    
    # Send verification email
    background_tasks.add_task(
        email_service.send_verification_email,
        user.email,
        user.verification_token
    )
    
    return user


@app.get("/api/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: str, db: Session = Depends(get_db)):
    """Get user by ID"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.put("/api/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    db: Session = Depends(get_db)
):
    """Update user preferences"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Validate province IDs if provided
    if user_update.province_ids:
        valid_provinces = db.query(Province).filter(Province.id.in_(user_update.province_ids)).all()
        if len(valid_provinces) != len(user_update.province_ids):
            raise HTTPException(status_code=400, detail="Invalid province IDs")
    
    # Update user fields
    update_data = user_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    
    return user


@app.post("/api/users/verify")
async def verify_email(token: str, db: Session = Depends(get_db)):
    """Verify user email with token"""
    user = db.query(User).filter(User.verification_token == token).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid verification token")
    
    user.email_verified = True
    user.verification_token = None
    db.commit()
    
    return {"message": "Email verified successfully"}


@app.delete("/api/users/{user_id}")
async def unsubscribe_user(user_id: str, db: Session = Depends(get_db)):
    """Unsubscribe user from alerts"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_active = False
    db.commit()
    
    return {"message": "User unsubscribed successfully"}


# Province endpoints
@app.get("/api/provinces/", response_model=List[ProvinceResponse])
async def get_provinces(db: Session = Depends(get_db)):
    """Get all provinces"""
    provinces = db.query(Province).order_by(Province.name).all()
    return provinces


@app.get("/api/provinces/{province_id}", response_model=ProvinceResponse)
async def get_province(province_id: int, db: Session = Depends(get_db)):
    """Get province by ID"""
    province = db.query(Province).filter(Province.id == province_id).first()
    if not province:
        raise HTTPException(status_code=404, detail="Province not found")
    return province


# Data access endpoints
@app.get("/api/stats/", response_model=List[DailyStatsResponse])
async def get_stats(
    province_ids: List[int] = Query(None),
    start_date: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    end_date: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    days: Optional[int] = Query(7, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """Get province statistics"""
    query = db.query(DailyStats)
    
    # Filter by provinces
    if province_ids:
        query = query.filter(DailyStats.province_id.in_(province_ids))
    
    # Filter by date range
    if start_date and end_date:
        query = query.filter(DailyStats.date >= start_date, DailyStats.date <= end_date)
    elif not start_date and not end_date:
        # Default to last N days
        start_date = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%d')
        query = query.filter(DailyStats.date >= start_date)
    
    stats = query.order_by(DailyStats.date.desc(), DailyStats.province_id).limit(1000).all()
    return stats


@app.get("/api/stats/current", response_model=List[DailyStatsResponse])
async def get_current_stats(
    province_ids: List[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Get current day statistics"""
    today = datetime.utcnow().strftime('%Y-%m-%d')
    query = db.query(DailyStats).filter(DailyStats.date == today)
    
    if province_ids:
        query = query.filter(DailyStats.province_id.in_(province_ids))
    
    stats = query.order_by(DailyStats.province_id).all()
    return stats


@app.get("/api/stats/province/{province_id}", response_model=List[DailyStatsResponse])
async def get_province_stats(
    province_id: int,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """Get time series for specific province"""
    start_date = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%d')
    
    stats = db.query(DailyStats).filter(
        DailyStats.province_id == province_id,
        DailyStats.date >= start_date
    ).order_by(DailyStats.date.desc()).all()
    
    return stats


# Alert endpoints
@app.get("/api/alerts/user/{user_id}", response_model=List[AlertResponse])
async def get_user_alerts(
    user_id: str,
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db)
):
    """Get user's recent alerts"""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    alerts = db.query(Alert).filter(
        Alert.user_id == user_id,
        Alert.created_at >= start_date
    ).order_by(Alert.created_at.desc()).limit(50).all()
    
    return alerts


# System status endpoints
@app.get("/api/system/status")
async def get_system_status(db: Session = Depends(get_db)):
    """Get system pipeline status"""
    from .database import SystemStatus
    
    # Get latest status for each component
    today = datetime.utcnow().strftime('%Y-%m-%d')
    statuses = db.query(SystemStatus).filter(SystemStatus.date == today).all()
    
    status_summary = {}
    for status in statuses:
        status_summary[status.component] = {
            "status": status.status,
            "message": status.message,
            "data_coverage_pct": status.data_coverage_pct,
            "updated_at": status.created_at.isoformat()
        }
    
    return {
        "date": today,
        "components": status_summary,
        "overall_status": "healthy" if all(s.get("status") == "success" for s in status_summary.values()) else "degraded"
    }


@app.get("/api/system/pipeline-logs")
async def get_pipeline_logs(
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db)
):
    """Get pipeline execution logs"""
    from .database import SystemStatus
    
    start_date = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%d')
    
    logs = db.query(SystemStatus).filter(
        SystemStatus.date >= start_date
    ).order_by(SystemStatus.created_at.desc()).limit(200).all()
    
    return [
        {
            "date": log.date,
            "component": log.component,
            "status": log.status,
            "message": log.message,
            "processing_time": log.processing_time_seconds,
            "data_coverage": log.data_coverage_pct,
            "timestamp": log.created_at.isoformat()
        }
        for log in logs
    ]


# Data ingestion endpoints (for pipeline)
@app.post("/api/data/daily-stats")
async def upload_daily_stats(
    stats_data: List[Dict[str, Any]],
    db: Session = Depends(get_db)
):
    """Upload daily statistics from pipeline"""
    try:
        db_manager.store_daily_stats(db, stats_data)
        return {"message": f"Stored {len(stats_data)} daily statistics"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store data: {str(e)}")


@app.post("/api/data/system-status")
async def upload_system_status(
    status_data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Upload system status from pipeline"""
    from .database import SystemStatus
    
    try:
        status = SystemStatus(**status_data)
        db.add(status)
        db.commit()
        return {"message": "System status recorded"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to record status: {str(e)}")


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }


# Background task for processing alerts
async def process_alert_queue():
    """Background task to process pending alerts"""
    with db_manager.get_session() as db:
        pending_alerts = db_manager.get_pending_alerts(db, limit=50)
        
        for alert in pending_alerts:
            try:
                # Get user details
                user = db.query(User).filter(User.id == alert.user_id).first()
                if not user or not user.is_active or not user.email_verified:
                    db_manager.mark_alert_sent(db, alert.id, error="User inactive or unverified")
                    continue
                
                # Get province name
                province = db.query(Province).filter(Province.id == alert.province_id).first()
                province_name = province.name if province else f"Province {alert.province_id}"
                
                # Send email
                success = email_service.send_alert_email(
                    user.email,
                    {
                        "province_name": province_name,
                        "alert_level": alert.alert_level,
                        "pm25_value": alert.pm25_value,
                        "health_message": alert.health_message,
                        "dust_detected": alert.dust_detected,
                        "forecast_hours": alert.forecast_hours
                    }
                )
                
                if success:
                    db_manager.mark_alert_sent(db, alert.id)
                else:
                    db_manager.mark_alert_sent(db, alert.id, error="Email delivery failed")
                    
            except Exception as e:
                db_manager.mark_alert_sent(db, alert.id, error=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
