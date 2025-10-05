"""
Dust alert system with personalized thresholds and notification queue
Handles risk assessment, threshold evaluation, and alert generation
"""
import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from dataclasses import dataclass
from enum import Enum


class AlertLevel(Enum):
    """Alert severity levels"""
    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    EXTREME = "extreme"


class HealthGroup(Enum):
    """User health sensitivity groups"""
    GENERAL = "general"          # General population
    SENSITIVE = "sensitive"      # Children, elderly, outdoor workers
    RESPIRATORY = "respiratory"  # Asthma, COPD, respiratory conditions
    CARDIAC = "cardiac"         # Heart conditions


@dataclass
class UserProfile:
    """User alert preferences and thresholds"""
    user_id: str
    email: str
    province_ids: List[int]
    health_group: HealthGroup
    
    # Custom thresholds (PM2.5 μg/m³)
    pm25_low_threshold: float = 15.0
    pm25_moderate_threshold: float = 25.0
    pm25_high_threshold: float = 50.0
    
    # Dust-specific thresholds
    dust_aod_threshold: float = 0.15
    dust_pm25_threshold: float = 30.0
    
    # Notification preferences
    notify_forecast: bool = True
    notify_current: bool = True
    quiet_hours_start: int = 22  # 22:00
    quiet_hours_end: int = 7     # 07:00
    max_alerts_per_day: int = 3
    
    # Alert history
    last_alert_time: Optional[datetime] = None
    daily_alert_count: int = 0
    last_alert_date: Optional[str] = None


@dataclass
class AlertData:
    """Alert information structure"""
    user_id: str
    province_name: str
    alert_level: AlertLevel
    pm25_value: float
    pm25_threshold: float
    dust_detected: bool
    dust_intensity: str
    health_message: str
    forecast_hours: int = 0  # 0 = current, >0 = forecast
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class PersonalizedAlertSystem:
    """Personalized dust alert system"""
    
    def __init__(self, params: dict):
        self.params = params
        self.data_dir = params["paths"]["derived_dir"]
        self.alert_queue_file = os.path.join(self.data_dir, "alert_queue.json")
        self.user_profiles_file = os.path.join(self.data_dir, "user_profiles.json")
        
        # Load user profiles
        self.user_profiles = self._load_user_profiles()
        
        # Health group thresholds (PM2.5 μg/m³)
        self.health_thresholds = {
            HealthGroup.GENERAL: {"low": 15, "moderate": 25, "high": 50},
            HealthGroup.SENSITIVE: {"low": 12, "moderate": 20, "high": 35},
            HealthGroup.RESPIRATORY: {"low": 10, "moderate": 15, "high": 25},
            HealthGroup.CARDIAC: {"low": 8, "moderate": 12, "high": 20},
        }
    
    def _load_user_profiles(self) -> Dict[str, UserProfile]:
        """Load user profiles from file"""
        if not os.path.exists(self.user_profiles_file):
            # Create sample profiles for testing
            return self._create_sample_profiles()
        
        try:
            with open(self.user_profiles_file, 'r') as f:
                data = json.load(f)
            
            profiles = {}
            for user_id, profile_data in data.items():
                profile_data['health_group'] = HealthGroup(profile_data['health_group'])
                if 'last_alert_time' in profile_data and profile_data['last_alert_time']:
                    profile_data['last_alert_time'] = datetime.fromisoformat(profile_data['last_alert_time'])
                profiles[user_id] = UserProfile(**profile_data)
            
            return profiles
            
        except Exception as e:
            print(f"Error loading user profiles: {e}")
            return self._create_sample_profiles()
    
    def _create_sample_profiles(self) -> Dict[str, UserProfile]:
        """Create sample user profiles for testing"""
        profiles = {
            "user_001": UserProfile(
                user_id="user_001",
                email="istanbul.resident@example.com",
                province_ids=[1],  # Istanbul
                health_group=HealthGroup.GENERAL,
                pm25_moderate_threshold=50.0
            ),
            "user_002": UserProfile(
                user_id="user_002", 
                email="ankara.sensitive@example.com",
                province_ids=[2],  # Ankara
                health_group=HealthGroup.SENSITIVE,
                pm25_low_threshold=15.0,
                pm25_moderate_threshold=35.0
            ),
            "user_003": UserProfile(
                user_id="user_003",
                email="southeast.respiratory@example.com", 
                province_ids=[8, 9],  # Sanliurfa, Gaziantep
                health_group=HealthGroup.RESPIRATORY,
                pm25_low_threshold=12.0,
                pm25_moderate_threshold=25.0,
                dust_aod_threshold=0.1
            ),
        }
        
        # Save sample profiles
        self._save_user_profiles(profiles)
        return profiles
    
    def _save_user_profiles(self, profiles: Dict[str, UserProfile]):
        """Save user profiles to file"""
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Convert to serializable format
        serializable_data = {}
        for user_id, profile in profiles.items():
            profile_dict = profile.__dict__.copy()
            profile_dict['health_group'] = profile.health_group.value
            if profile.last_alert_time:
                profile_dict['last_alert_time'] = profile.last_alert_time.isoformat()
            serializable_data[user_id] = profile_dict
        
        with open(self.user_profiles_file, 'w') as f:
            json.dump(serializable_data, f, indent=2)
    
    def evaluate_alert_level(self, pm25: float, profile: UserProfile, dust_data: dict) -> Tuple[AlertLevel, str]:
        """Evaluate alert level for a user based on PM2.5 and dust conditions"""
        # Get health-group specific thresholds
        base_thresholds = self.health_thresholds[profile.health_group]
        
        # Use custom thresholds if set
        low_threshold = getattr(profile, 'pm25_low_threshold', base_thresholds['low'])
        moderate_threshold = getattr(profile, 'pm25_moderate_threshold', base_thresholds['moderate'])
        high_threshold = getattr(profile, 'pm25_high_threshold', base_thresholds['high'])
        
        # Check dust conditions
        dust_detected = dust_data.get('dust_event_detected', False)
        dust_aod = dust_data.get('dust_aod_mean', 0.0)
        dust_intensity = dust_data.get('dust_intensity', 'None')
        
        # Determine alert level
        if pm25 >= high_threshold or (dust_detected and dust_aod > 0.4):
            level = AlertLevel.HIGH
            if pm25 >= 100 or dust_aod > 0.6:
                level = AlertLevel.EXTREME
        elif pm25 >= moderate_threshold or (dust_detected and dust_aod > profile.dust_aod_threshold):
            level = AlertLevel.MODERATE
        elif pm25 >= low_threshold or dust_aod > 0.05:
            level = AlertLevel.LOW
        else:
            level = AlertLevel.NONE
        
        # Generate health message
        message = self._generate_health_message(level, profile.health_group, dust_detected, dust_intensity)
        
        return level, message
    
    def _generate_health_message(self, level: AlertLevel, health_group: HealthGroup, 
                                dust_detected: bool, dust_intensity: str) -> str:
        """Generate personalized health message"""
        dust_intensity_str = str(dust_intensity) if dust_intensity is not None else "unknown"
        dust_msg = f" Dust event ({dust_intensity_str.lower()}) detected." if dust_detected else ""
        
        messages = {
            AlertLevel.NONE: {
                HealthGroup.GENERAL: "Air quality is good. Enjoy outdoor activities.",
                HealthGroup.SENSITIVE: "Air quality is acceptable for sensitive individuals.",
                HealthGroup.RESPIRATORY: "Good conditions for outdoor activities.",
                HealthGroup.CARDIAC: "Favorable air quality for all activities."
            },
            AlertLevel.LOW: {
                HealthGroup.GENERAL: f"Moderate air quality. Consider reducing prolonged outdoor exertion.{dust_msg}",
                HealthGroup.SENSITIVE: f"Limit outdoor activities if you experience symptoms.{dust_msg}",
                HealthGroup.RESPIRATORY: f"Consider wearing a mask outdoors. Monitor symptoms.{dust_msg}",
                HealthGroup.CARDIAC: f"Limit strenuous outdoor activities.{dust_msg}"
            },
            AlertLevel.MODERATE: {
                HealthGroup.GENERAL: f"Unhealthy for sensitive groups. Limit outdoor exertion.{dust_msg}",
                HealthGroup.SENSITIVE: f"Avoid outdoor activities. Stay indoors if possible.{dust_msg}",
                HealthGroup.RESPIRATORY: f"Stay indoors. Use air purifiers if available.{dust_msg}",
                HealthGroup.CARDIAC: f"Avoid outdoor activities. Monitor health closely.{dust_msg}"
            },
            AlertLevel.HIGH: {
                HealthGroup.GENERAL: f"Unhealthy air quality. Avoid outdoor activities.{dust_msg}",
                HealthGroup.SENSITIVE: f"Stay indoors. Avoid all outdoor activities.{dust_msg}", 
                HealthGroup.RESPIRATORY: f"Emergency conditions. Stay indoors with air filtration.{dust_msg}",
                HealthGroup.CARDIAC: f"Health emergency. Stay indoors and monitor symptoms.{dust_msg}"
            },
            AlertLevel.EXTREME: {
                HealthGroup.GENERAL: f"Hazardous air quality. Emergency conditions for all.{dust_msg}",
                HealthGroup.SENSITIVE: f"Health emergency. Stay indoors with air filtration.{dust_msg}",
                HealthGroup.RESPIRATORY: f"Medical emergency. Seek medical attention if needed.{dust_msg}",
                HealthGroup.CARDIAC: f"Medical emergency. Contact healthcare provider.{dust_msg}"
            }
        }
        
        return messages[level][health_group]
    
    def should_send_alert(self, user_profile: UserProfile, alert_level: AlertLevel) -> bool:
        """Check if alert should be sent based on user preferences and rate limiting"""
        if alert_level == AlertLevel.NONE:
            return False
        
        now = datetime.utcnow()
        
        # Check quiet hours (Turkish time = UTC+3)
        turkey_hour = (now.hour + 3) % 24
        if user_profile.quiet_hours_start <= turkey_hour or turkey_hour <= user_profile.quiet_hours_end:
            if alert_level not in [AlertLevel.HIGH, AlertLevel.EXTREME]:
                return False  # Skip non-critical alerts during quiet hours
        
        # Reset daily counter if new day
        today = now.date().isoformat()
        if user_profile.last_alert_date != today:
            user_profile.daily_alert_count = 0
            user_profile.last_alert_date = today
        
        # Check daily limit (except for high/extreme alerts)
        if alert_level not in [AlertLevel.HIGH, AlertLevel.EXTREME]:
            if user_profile.daily_alert_count >= user_profile.max_alerts_per_day:
                return False
        
        # Check minimum time between alerts (except emergency)
        if user_profile.last_alert_time and alert_level not in [AlertLevel.HIGH, AlertLevel.EXTREME]:
            time_since_last = now - user_profile.last_alert_time
            if time_since_last < timedelta(hours=4):  # 4-hour minimum gap
                return False
        
        return True
    
    def process_daily_alerts(self, pm25_csv_path: str, forecast_csv_path: str = None) -> List[AlertData]:
        """Process daily alerts for all users"""
        # Load current conditions
        df_current = pd.read_csv(pm25_csv_path)
        
        alerts = []
        
        for user_id, profile in self.user_profiles.items():
            # Check each province the user monitors
            for province_id in profile.province_ids:
                province_data = df_current[df_current['province_id'] == province_id]
                
                if len(province_data) == 0:
                    continue
                
                row = province_data.iloc[0]
                
                # Evaluate current conditions
                dust_data = {
                    'dust_event_detected': row.get('dust_event_detected', False),
                    'dust_aod_mean': row.get('dust_aod_mean', 0.0),
                    'dust_intensity': row.get('dust_intensity', 'None')
                }
                
                alert_level, health_message = self.evaluate_alert_level(
                    row['pm25'], profile, dust_data
                )
                
                # Check if alert should be sent
                if self.should_send_alert(profile, alert_level):
                    alert = AlertData(
                        user_id=user_id,
                        province_name=row['province_name'],
                        alert_level=alert_level,
                        pm25_value=row['pm25'],
                        pm25_threshold=profile.pm25_moderate_threshold,
                        dust_detected=dust_data['dust_event_detected'],
                        dust_intensity=dust_data['dust_intensity'],
                        health_message=health_message,
                        forecast_hours=0
                    )
                    
                    alerts.append(alert)
                    
                    # Update user profile
                    profile.last_alert_time = datetime.utcnow()
                    profile.daily_alert_count += 1
        
        # Save updated profiles
        self._save_user_profiles(self.user_profiles)
        
        # Queue alerts for sending
        self._queue_alerts(alerts)
        
        return alerts
    
    def _queue_alerts(self, alerts: List[AlertData]):
        """Add alerts to email queue"""
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Load existing queue
        queue = []
        if os.path.exists(self.alert_queue_file):
            try:
                with open(self.alert_queue_file, 'r') as f:
                    queue_data = json.load(f)
                    for item in queue_data:
                        item['alert_level'] = AlertLevel(item['alert_level'])
                        item['timestamp'] = datetime.fromisoformat(item['timestamp'])
                    queue = queue_data
            except Exception as e:
                # Backup invalid JSON and continue with an empty queue
                try:
                    backup_path = self.alert_queue_file + ".bak"
                    with open(self.alert_queue_file, 'r', errors='ignore') as bad:
                        bad_content = bad.read()
                    with open(backup_path, 'w', encoding='utf-8') as out:
                        out.write(bad_content)
                    print(f"Error loading alert queue: {e}. Backed up to {backup_path} and continuing with empty queue.")
                except Exception as be:
                    print(f"Error backing up invalid alert queue: {be}")
        
        # Add new alerts
        for alert in alerts:
            alert_dict = alert.__dict__.copy()
            # Convert enums and datetime to JSON-serializable types
            alert_dict['alert_level'] = alert.alert_level.value if hasattr(alert.alert_level, 'value') else str(alert.alert_level)
            alert_dict['timestamp'] = alert.timestamp.isoformat() if hasattr(alert.timestamp, 'isoformat') else str(alert.timestamp)
            # Ensure booleans are proper JSON booleans
            alert_dict['dust_detected'] = bool(alert_dict.get('dust_detected', False))
            queue.append(alert_dict)
        
        # Save queue
        with open(self.alert_queue_file, 'w') as f:
            json.dump(queue, f, indent=2)
        
        print(f"Queued {len(alerts)} alerts for delivery")


def generate_alerts_for_day(utc_date: datetime, pm25_csv_path: str, params: dict) -> str:
    """
    Generate personalized alerts for a day
    Returns path to alert queue file
    """
    alert_system = PersonalizedAlertSystem(params)
    alerts = alert_system.process_daily_alerts(pm25_csv_path)
    
    print(f"Generated {len(alerts)} alerts for {utc_date.date()}")
    
    # Summary by alert level
    level_counts = {}
    for alert in alerts:
        level = alert.alert_level.value
        level_counts[level] = level_counts.get(level, 0) + 1
    
    if level_counts:
        print("Alert summary:")
        for level, count in level_counts.items():
            print(f"  {level.title()}: {count}")
    
    return alert_system.alert_queue_file


if __name__ == "__main__":
    # Test alert system
    import yaml
    
    config_path = "../config/params.yaml"
    with open(config_path) as f:
        params = yaml.safe_load(f)
    
    # Create test PM2.5 data
    test_data = pd.DataFrame({
        'province_id': [1, 2, 8, 9],
        'province_name': ['Istanbul', 'Ankara', 'Sanliurfa', 'Gaziantep'],
        'pm25': [35.0, 28.0, 65.0, 45.0],
        'dust_event_detected': [False, False, True, True],
        'dust_aod_mean': [0.05, 0.03, 0.25, 0.18],
        'dust_intensity': ['None', 'None', 'Moderate', 'Light']
    })
    
    test_csv = os.path.join(params["paths"]["derived_dir"], "test_pm25.csv")
    os.makedirs(params["paths"]["derived_dir"], exist_ok=True)
    test_data.to_csv(test_csv, index=False)
    
    # Generate alerts
    alert_file = generate_alerts_for_day(datetime.now(), test_csv, params)
    print(f"Alert queue saved to: {alert_file}")
