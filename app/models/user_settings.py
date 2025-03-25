# app/models/user_settings.py
from app import db
from datetime import datetime

class UserSettings(db.Model):
    __tablename__ = 'user_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    theme = db.Column(db.Boolean, default=False)  # False = light, True = dark
    language = db.Column(db.String(10), default='en')
    currency = db.Column(db.String(10), default='USD')
    default_crypto = db.Column(db.String(10), default='USDT')
    time_format = db.Column(db.String(5), default='12h')
    date_format = db.Column(db.String(20), default='MM/DD/YYYY')
    
    # Notification settings stored as JSON
    notifications_json = db.Column(db.Text, default='{"priceAlerts":true,"tradeConfirmations":true,"newsUpdates":false,"signalAlerts":true,"emailNotifications":true}')
    
    # Security settings stored as JSON
    security_json = db.Column(db.Text, default='{"twoFactor":false,"sessionTimeout":"30","rememberLogin":true,"biometric":false}')
    
    # Trading settings stored as JSON
    trading_json = db.Column(db.Text, default='{"confirmations":true,"defaultChartTimeframe":"1d","showOrderbook":true,"riskProtection":"2","autoConvert":false}')
    
    # Display settings stored as JSON
    display_json = db.Column(db.Text, default='{"compactMode":false,"showBalance":true,"chartStyle":"candle","fontSize":"medium"}')
    
    # Privacy settings stored as JSON
    privacy_json = db.Column(db.Text, default='{"anonymousTrading":true,"usageAnalytics":true}')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship with User
    user = db.relationship('User', backref=db.backref('settings', uselist=False))
    
    def __repr__(self):
        return f"UserSettings(User: {self.user_id})"