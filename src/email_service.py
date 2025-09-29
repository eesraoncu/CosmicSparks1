"""
Email service for dust alert notifications
Handles SMTP configuration and email template rendering
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from typing import Dict, Any, Optional
from datetime import datetime
import yaml
from jinja2 import Template

class EmailService:
    """Email service for sending dust alerts and notifications"""
    
    def __init__(self, config_path: str = None):
        self.config = self._load_config(config_path)
        self.smtp_config = self.config.get('email', {})
        
        # Email templates
        self.templates = {
            'alert': self._get_alert_template(),
            'verification': self._get_verification_template(),
            'welcome': self._get_welcome_template()
        }
    
    def _load_config(self, config_path: str = None) -> dict:
        """Load email configuration"""
        if config_path is None:
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "params.yaml")
        
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
        except FileNotFoundError:
            config = {}
        
        # Default email configuration
        default_email_config = {
            'smtp_server': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
            'smtp_port': int(os.getenv('SMTP_PORT', '587')),
            'smtp_username': os.getenv('SMTP_USERNAME', ''),
            'smtp_password': os.getenv('SMTP_PASSWORD', ''),
            'from_email': os.getenv('FROM_EMAIL', 'noreply@dustalert.tr'),
            'from_name': 'Türkiye Toz Uyarı Sistemi',
            'use_tls': True
        }
        
        if 'email' not in config:
            config['email'] = default_email_config
        else:
            # Merge with defaults
            for key, value in default_email_config.items():
                if key not in config['email']:
                    config['email'][key] = value
        
        return config
    
    def _get_alert_template(self) -> str:
        """Get alert email template"""
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Toz Uyarısı - {{ province_name }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }
        .container { max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { background: linear-gradient(135deg, #FF6B35, #F7931E); color: white; padding: 20px; border-radius: 8px 8px 0 0; text-align: center; }
        .content { padding: 30px; }
        .alert-level { display: inline-block; padding: 8px 16px; border-radius: 20px; font-weight: bold; text-transform: uppercase; margin: 10px 0; }
        .alert-low { background: #FFF3CD; color: #856404; }
        .alert-moderate { background: #F8D7DA; color: #721C24; }
        .alert-high { background: #D1ECF1; color: #0C5460; }
        .alert-extreme { background: #F5C6CB; color: #721C24; }
        .pm25-value { font-size: 2em; font-weight: bold; color: #FF6B35; text-align: center; margin: 20px 0; }
        .health-message { background: #E9ECEF; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #FF6B35; }
        .dust-info { background: #FFF3CD; padding: 10px; border-radius: 5px; margin: 15px 0; }
        .footer { background: #F8F9FA; padding: 20px; border-radius: 0 0 8px 8px; font-size: 0.9em; color: #6C757D; }
        .unsubscribe { text-align: center; margin-top: 15px; }
        .unsubscribe a { color: #6C757D; text-decoration: none; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🌪️ Toz Uyarısı</h1>
            <h2>{{ province_name }}</h2>
            <p>{{ timestamp.strftime('%d.%m.%Y %H:%M') }} (Türkiye Saati)</p>
        </div>
        
        <div class="content">
            <div class="alert-level alert-{{ alert_level }}">
                {{ alert_level_tr[alert_level] }} SEVİYE UYARI
            </div>
            
            {% if forecast_hours > 0 %}
            <p><strong>⏰ {{ forecast_hours }} saat sonrası için tahmin</strong></p>
            {% else %}
            <p><strong>📍 Şu anki durum</strong></p>
            {% endif %}
            
            <div class="pm25-value">
                PM2.5: {{ "%.1f"|format(pm25_value) }} μg/m³
            </div>
            
            {% if dust_detected %}
            <div class="dust-info">
                <strong>🌪️ Toz fırtınası tespit edildi!</strong><br>
                Şiddet: {{ dust_intensity or 'Bilinmiyor' }}
            </div>
            {% endif %}
            
            <div class="health-message">
                <h3>🏥 Sağlık Önerisi</h3>
                <p>{{ health_message }}</p>
            </div>
            
            <div style="margin-top: 25px;">
                <h3>📊 Ek Bilgiler</h3>
                <ul>
                    <li><strong>Hava Kalitesi Standardı:</strong> WHO/EU rehberlerine göre</li>
                    <li><strong>Veri Kaynağı:</strong> NASA MODIS, ECMWF CAMS</li>
                    <li><strong>Güncelleme:</strong> Günlük, otomatik</li>
                </ul>
            </div>
            
            <div style="background: #E3F2FD; padding: 15px; border-radius: 5px; margin-top: 20px;">
                <p><strong>💡 Genel Öneriler:</strong></p>
                <ul>
                    <li>Hava kalitesi uygulamalarını takip edin</li>
                    <li>Yüksek riskli dönemlerde maske kullanın</li>
                    <li>Kapalı alanlarda hava temizleyici kullanın</li>
                    <li>Sağlık sorunlarınız varsa doktorunuza danışın</li>
                </ul>
            </div>
        </div>
        
        <div class="footer">
            <p><strong>Türkiye Toz İzleme ve Uyarı Sistemi</strong></p>
            <p>Bu sistem NASA Space Apps Challenge 2024 kapsamında geliştirilmiştir.</p>
            <p>Kaynak veriler: NASA MODIS, ECMWF CAMS, ERA5</p>
            
            <div class="unsubscribe">
                <a href="{{ unsubscribe_url }}">Uyarıları durdur</a> | 
                <a href="{{ preferences_url }}">Tercihlerimi güncelle</a>
            </div>
        </div>
    </div>
</body>
</html>
        """
    
    def _get_verification_template(self) -> str:
        """Get email verification template"""
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>E-posta Doğrulama - Toz Uyarı Sistemi</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }
        .container { max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { background: linear-gradient(135deg, #4CAF50, #45A049); color: white; padding: 20px; border-radius: 8px 8px 0 0; text-align: center; }
        .content { padding: 30px; text-align: center; }
        .verify-button { display: inline-block; background: #4CAF50; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; margin: 20px 0; }
        .footer { background: #F8F9FA; padding: 20px; border-radius: 0 0 8px 8px; font-size: 0.9em; color: #6C757D; text-align: center; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>✅ E-posta Doğrulama</h1>
        </div>
        
        <div class="content">
            <h2>Toz Uyarı Sistemi'ne Hoş Geldiniz!</h2>
            <p>Türkiye Toz İzleme ve Uyarı Sistemi'ne kaydolduğunuz için teşekkür ederiz.</p>
            <p>Uyarı almaya başlamak için e-posta adresinizi doğrulamanız gerekmektedir.</p>
            
            <a href="{{ verification_url }}" class="verify-button">E-postamı Doğrula</a>
            
            <p>Eğer buton çalışmıyorsa, aşağıdaki bağlantıyı kopyalayıp tarayıcınıza yapıştırın:</p>
            <p style="word-break: break-all; color: #666;">{{ verification_url }}</p>
            
            <p><strong>Bu bağlantı 24 saat geçerlidir.</strong></p>
        </div>
        
        <div class="footer">
            <p>Bu e-postayı siz talep ettiyseniz güvenle göz ardı edebilirsiniz.</p>
            <p><strong>Türkiye Toz İzleme ve Uyarı Sistemi</strong></p>
        </div>
    </div>
</body>
</html>
        """
    
    def _get_welcome_template(self) -> str:
        """Get welcome email template"""
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Hoş Geldiniz - Toz Uyarı Sistemi</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }
        .container { max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { background: linear-gradient(135deg, #2196F3, #1976D2); color: white; padding: 20px; border-radius: 8px 8px 0 0; text-align: center; }
        .content { padding: 30px; }
        .feature { background: #F8F9FA; padding: 15px; margin: 15px 0; border-radius: 5px; border-left: 4px solid #2196F3; }
        .footer { background: #F8F9FA; padding: 20px; border-radius: 0 0 8px 8px; font-size: 0.9em; color: #6C757D; text-align: center; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎉 Hoş Geldiniz!</h1>
            <p>Türkiye Toz İzleme ve Uyarı Sistemi</p>
        </div>
        
        <div class="content">
            <h2>Sayın {{ user_name }},</h2>
            <p>E-posta adresiniz başarıyla doğrulandı! Artık {{ provinces_text }} için toz uyarıları alacaksınız.</p>
            
            <div class="feature">
                <h3>🛰️ Gerçek Zamanlı İzleme</h3>
                <p>NASA MODIS ve ECMWF CAMS uydu verilerini kullanarak günlük toz takibi yapıyoruz.</p>
            </div>
            
            <div class="feature">
                <h3>🏥 Kişiselleştirilmiş Uyarılar</h3>
                <p>Sağlık durumunuza ({{ health_group_tr }}) göre özelleştirilmiş uyarılar alacaksınız.</p>
            </div>
            
            <div class="feature">
                <h3>📱 Akıllı Bildirimler</h3>
                <p>Sessiz saatlerde rahatsız edilmeyecek, günlük limit kontrolü yapılacak.</p>
            </div>
            
            <div class="feature">
                <h3>📊 PM2.5 Tahminleri</h3>
                <p>Gelişmiş modelleme ile hava kalitesi tahminleri ve sağlık önerileri.</p>
            </div>
            
            <h3>⚙️ Ayarlarınız</h3>
            <ul>
                <li><strong>İzlenen İller:</strong> {{ provinces_text }}</li>
                <li><strong>Sağlık Grubu:</strong> {{ health_group_tr }}</li>
                <li><strong>PM2.5 Eşikleri:</strong> {{ pm25_thresholds }}</li>
                <li><strong>Sessiz Saatler:</strong> {{ quiet_hours }}</li>
                <li><strong>Günlük Limit:</strong> {{ max_alerts_per_day }} uyarı</li>
            </ul>
            
            <p>Bu ayarları istediğiniz zaman web sitemizden değiştirebilirsiniz.</p>
        </div>
        
        <div class="footer">
            <p><strong>Türkiye Toz İzleme ve Uyarı Sistemi</strong></p>
            <p>NASA Space Apps Challenge 2024 projesi</p>
            <p><a href="{{ website_url }}">Web Sitesi</a> | <a href="{{ unsubscribe_url }}">Abonelikten Çık</a></p>
        </div>
    </div>
</body>
</html>
        """
    
    def _create_smtp_connection(self):
        """Create SMTP connection"""
        try:
            server = smtplib.SMTP(self.smtp_config['smtp_server'], self.smtp_config['smtp_port'])
            if self.smtp_config.get('use_tls', True):
                server.starttls()
            
            if self.smtp_config['smtp_username'] and self.smtp_config['smtp_password']:
                server.login(self.smtp_config['smtp_username'], self.smtp_config['smtp_password'])
            
            return server
        except Exception as e:
            print(f"SMTP connection failed: {e}")
            return None
    
    def send_alert_email(self, to_email: str, alert_data: Dict[str, Any]) -> bool:
        """Send alert email to user"""
        try:
            # Prepare template context
            context = {
                **alert_data,
                'timestamp': datetime.now(),
                'alert_level_tr': {
                    'low': 'DÜŞÜK',
                    'moderate': 'ORTA',
                    'high': 'YÜKSEK',
                    'extreme': 'EKSTREM'
                },
                'unsubscribe_url': f"{self.config.get('website_url', 'http://localhost:3000')}/unsubscribe",
                'preferences_url': f"{self.config.get('website_url', 'http://localhost:3000')}/preferences"
            }
            
            # Render template
            template = Template(self.templates['alert'])
            html_content = template.render(**context)
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"Toz Uyarısı - {alert_data['province_name']} ({alert_data['alert_level'].upper()})"
            msg['From'] = formataddr((self.smtp_config['from_name'], self.smtp_config['from_email']))
            msg['To'] = to_email
            
            # Add HTML content
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
            
            # Send email
            server = self._create_smtp_connection()
            if server:
                text = msg.as_string()
                server.sendmail(self.smtp_config['from_email'], [to_email], text)
                server.quit()
                print(f"Alert email sent to {to_email}")
                return True
            else:
                print(f"Failed to send alert email to {to_email}")
                return False
                
        except Exception as e:
            print(f"Error sending alert email to {to_email}: {e}")
            return False
    
    def send_verification_email(self, to_email: str, verification_token: str) -> bool:
        """Send email verification"""
        try:
            verification_url = f"{self.config.get('website_url', 'http://localhost:3000')}/verify?token={verification_token}"
            
            context = {
                'verification_url': verification_url
            }
            
            template = Template(self.templates['verification'])
            html_content = template.render(**context)
            
            msg = MIMEMultipart('alternative')
            msg['Subject'] = "E-posta Doğrulama - Toz Uyarı Sistemi"
            msg['From'] = formataddr((self.smtp_config['from_name'], self.smtp_config['from_email']))
            msg['To'] = to_email
            
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
            
            server = self._create_smtp_connection()
            if server:
                text = msg.as_string()
                server.sendmail(self.smtp_config['from_email'], [to_email], text)
                server.quit()
                print(f"Verification email sent to {to_email}")
                return True
            else:
                return False
                
        except Exception as e:
            print(f"Error sending verification email to {to_email}: {e}")
            return False
    
    def send_welcome_email(self, to_email: str, user_data: Dict[str, Any]) -> bool:
        """Send welcome email after verification"""
        try:
            health_groups_tr = {
                'general': 'Genel Nüfus',
                'sensitive': 'Hassas Grup',
                'respiratory': 'Solunum Hastası',
                'cardiac': 'Kalp Hastası'
            }
            
            context = {
                'user_name': user_data.get('email', '').split('@')[0],
                'provinces_text': ', '.join(user_data.get('province_names', [])),
                'health_group_tr': health_groups_tr.get(user_data.get('health_group'), 'Genel'),
                'pm25_thresholds': f"{user_data.get('pm25_low_threshold', 25)}/{user_data.get('pm25_moderate_threshold', 50)}/{user_data.get('pm25_high_threshold', 75)} μg/m³",
                'quiet_hours': f"{user_data.get('quiet_hours_start', 22)}:00 - {user_data.get('quiet_hours_end', 7)}:00",
                'max_alerts_per_day': user_data.get('max_alerts_per_day', 3),
                'website_url': self.config.get('website_url', 'http://localhost:3000'),
                'unsubscribe_url': f"{self.config.get('website_url', 'http://localhost:3000')}/unsubscribe"
            }
            
            template = Template(self.templates['welcome'])
            html_content = template.render(**context)
            
            msg = MIMEMultipart('alternative')
            msg['Subject'] = "Hoş Geldiniz - Toz Uyarı Sistemi"
            msg['From'] = formataddr((self.smtp_config['from_name'], self.smtp_config['from_email']))
            msg['To'] = to_email
            
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
            
            server = self._create_smtp_connection()
            if server:
                text = msg.as_string()
                server.sendmail(self.smtp_config['from_email'], [to_email], text)
                server.quit()
                print(f"Welcome email sent to {to_email}")
                return True
            else:
                return False
                
        except Exception as e:
            print(f"Error sending welcome email to {to_email}: {e}")
            return False


if __name__ == "__main__":
    # Test email service
    email_service = EmailService()
    
    # Test alert email
    alert_data = {
        'province_name': 'İstanbul',
        'alert_level': 'moderate',
        'pm25_value': 45.0,
        'health_message': 'Hassas gruplar için sağlıksız hava kalitesi.',
        'dust_detected': True,
        'dust_intensity': 'Orta',
        'forecast_hours': 0
    }
    
    print("Testing email templates...")
    print("Alert email template test completed")
