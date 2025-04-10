# app/config.py
import os
from datetime import timedelta

class Config:
    # Basic config
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a-very-hard-to-guess-string'
    DEBUG = os.environ.get('FLASK_DEBUG', False)
    ENVIRONMENT = os.environ.get('FLASK_ENV', 'production')
    
    # Database config
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Flask-Login config
    REMEMBER_COOKIE_DURATION = timedelta(days=30)
    REMEMBER_COOKIE_SECURE = True
    REMEMBER_COOKIE_HTTPONLY = True
    
    # Mail settings for OTP and account verification
    MAIL_SERVER = 'smtp.hostinger.com'
    MAIL_PORT = 465
    MAIL_USE_SSL = True
    MAIL_USE_TLS = False
    MAIL_USERNAME = 'verify@theinvestro.io'  
    MAIL_PASSWORD = 'Root@Bloom@098'
    
    # New notification mail settings (for all other emails)
    NOTIFICATION_MAIL_SERVER = os.environ.get('NOTIFICATION_MAIL_SERVER', 'smtp.hostinger.com')
    NOTIFICATION_MAIL_PORT = int(os.environ.get('NOTIFICATION_MAIL_PORT', 465))
    NOTIFICATION_MAIL_USE_SSL = os.environ.get('NOTIFICATION_MAIL_USE_SSL', 'True').lower() == 'true'
    NOTIFICATION_MAIL_USE_TLS = os.environ.get('NOTIFICATION_MAIL_USE_TLS', 'False').lower() == 'true'
    NOTIFICATION_MAIL_USERNAME = os.environ.get('NOTIFICATION_MAIL_USERNAME', 'verify@theinvestro.io')
    NOTIFICATION_MAIL_PASSWORD = os.environ.get('NOTIFICATION_MAIL_PASSWORD', 'Root@Bloom@098')
    NOTIFICATION_MAIL_DEFAULT_SENDER = os.environ.get('NOTIFICATION_MAIL_DEFAULT_SENDER', 'Investro Notifications <notifications@theinvestro.io>')
    
    # File upload settings
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload
    
    # CoinGecko API settings
    COINGECKO_API_KEY = os.environ.get('COINGECKO_API_KEY', 'CG-xM4oVPrLjBmcUKq7Yv1J821D')
    
    # SMS API settings (placeholder for development)
    SMS_PROVIDER = os.environ.get('SMS_PROVIDER', 'twilio')
    SMS_API_KEY = os.environ.get('SMS_API_KEY')
    SMS_API_URL = os.environ.get('SMS_API_URL')
    SMS_API_PAYLOAD = os.environ.get('SMS_API_PAYLOAD', '{"phone":"{{phone}}","message":"{{message}}"}')
    SMS_API_HEADERS = os.environ.get('SMS_API_HEADERS', '{"Content-Type":"application/json"}')
    
    # Twilio settings
    TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
    TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
    TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER')
    
    # AWS settings for SNS (SMS)
    AWS_ACCESS_KEY = os.environ.get('AWS_ACCESS_KEY')
    AWS_SECRET_KEY = os.environ.get('AWS_SECRET_KEY')
    AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
    AWS_SNS_SENDER_ID = os.environ.get('AWS_SNS_SENDER_ID', 'Investro')
    
    # Push notification settings
    PUSH_PROVIDER = os.environ.get('PUSH_PROVIDER', 'fcm')
    FIREBASE_CREDENTIALS_PATH = os.environ.get('FIREBASE_CREDENTIALS_PATH')
    ONESIGNAL_APP_ID = os.environ.get('ONESIGNAL_APP_ID')
    ONESIGNAL_API_KEY = os.environ.get('ONESIGNAL_API_KEY')

class DevelopmentConfig(Config):
    DEBUG = True
    ENVIRONMENT = 'development'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///dev.db'
    REMEMBER_COOKIE_SECURE = False
    
class TestingConfig(Config):
    TESTING = True
    ENVIRONMENT = 'testing'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    REMEMBER_COOKIE_SECURE = False
    
class ProductionConfig(Config):
    DEBUG = False
    ENVIRONMENT = 'production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')