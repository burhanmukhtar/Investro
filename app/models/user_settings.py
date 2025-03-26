# app/models/user_settings.py - completely replace the existing file with this content

from app import db
from datetime import datetime
import json

class UserSettings(db.Model):
    """
    User settings model with improved handling and default values.
    """
    __tablename__ = 'user_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    
    # Basic settings
    theme = db.Column(db.Boolean, default=False)  # False = light, True = dark
    language = db.Column(db.String(10), default='en')
    currency = db.Column(db.String(10), default='USD')
    default_crypto = db.Column(db.String(10), default='USDT')
    time_format = db.Column(db.String(5), default='12h')
    date_format = db.Column(db.String(20), default='MM/DD/YYYY')
    
    # JSON settings storage
    notifications_json = db.Column(db.Text)
    security_json = db.Column(db.Text)
    trading_json = db.Column(db.Text)
    display_json = db.Column(db.Text)
    privacy_json = db.Column(db.Text)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship with User
    user = db.relationship('User', backref=db.backref('settings', uselist=False))
    
    def __init__(self, user_id):
        """Initialize with default settings"""
        self.user_id = user_id
        self.theme = False
        self.language = 'en'
        self.currency = 'USD'
        self.default_crypto = 'USDT'
        self.time_format = '12h'
        self.date_format = 'MM/DD/YYYY'
        
        # Set default JSON values
        self.notifications_json = json.dumps({
            "priceAlerts": True,
            "tradeConfirmations": True,
            "newsUpdates": False,
            "signalAlerts": True,
            "emailNotifications": True
        })
        
        self.security_json = json.dumps({
            "twoFactor": False,
            "sessionTimeout": "30",
            "rememberLogin": True,
            "biometric": False
        })
        
        self.trading_json = json.dumps({
            "confirmations": True,
            "defaultChartTimeframe": "1d",
            "showOrderbook": True,
            "riskProtection": "2",
            "autoConvert": False
        })
        
        self.display_json = json.dumps({
            "compactMode": False,
            "showBalance": True,
            "chartStyle": "candle",
            "fontSize": "medium"
        })
        
        # Continuation of app/models/user_settings.py

        self.privacy_json = json.dumps({
            "anonymousTrading": True,
            "usageAnalytics": True
        })
    
    def get_notifications(self):
        """Safely get notifications settings"""
        try:
            if self.notifications_json:
                return json.loads(self.notifications_json)
        except (json.JSONDecodeError, TypeError):
            pass
        
        # Return default if not found or error
        return {
            "priceAlerts": True,
            "tradeConfirmations": True,
            "newsUpdates": False,
            "signalAlerts": True,
            "emailNotifications": True
        }
    
    def get_security(self):
        """Safely get security settings"""
        try:
            if self.security_json:
                return json.loads(self.security_json)
        except (json.JSONDecodeError, TypeError):
            pass
        
        # Return default if not found or error
        return {
            "twoFactor": False,
            "sessionTimeout": "30",
            "rememberLogin": True,
            "biometric": False
        }
    
    def get_trading(self):
        """Safely get trading settings"""
        try:
            if self.trading_json:
                return json.loads(self.trading_json)
        except (json.JSONDecodeError, TypeError):
            pass
        
        # Return default if not found or error
        return {
            "confirmations": True,
            "defaultChartTimeframe": "1d",
            "showOrderbook": True,
            "riskProtection": "2",
            "autoConvert": False
        }
    
    def get_display(self):
        """Safely get display settings"""
        try:
            if self.display_json:
                return json.loads(self.display_json)
        except (json.JSONDecodeError, TypeError):
            pass
        
        # Return default if not found or error
        return {
            "compactMode": False,
            "showBalance": True,
            "chartStyle": "candle",
            "fontSize": "medium"
        }
    
    def get_privacy(self):
        """Safely get privacy settings"""
        try:
            if self.privacy_json:
                return json.loads(self.privacy_json)
        except (json.JSONDecodeError, TypeError):
            pass
        
        # Return default if not found or error
        return {
            "anonymousTrading": True,
            "usageAnalytics": True
        }
    
    def get_all_settings(self):
        """Get all settings in a client-friendly format"""
        return {
            "darkMode": self.theme,
            "language": self.language,
            "currency": self.currency,
            "defaultCrypto": self.default_crypto,
            "timeFormat": self.time_format,
            "dateFormat": self.date_format,
            "notifications": self.get_notifications(),
            "security": self.get_security(),
            "trading": self.get_trading(),
            "display": self.get_display(),
            "privacy": self.get_privacy(),
            "lastSaved": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def set_from_json(self, data):
        """Update settings from a client-submitted JSON object"""
        try:
            # Update basic settings
            if 'darkMode' in data:
                self.theme = bool(data['darkMode'])
            
            if 'language' in data:
                self.language = str(data['language'])
            
            if 'currency' in data:
                self.currency = str(data['currency'])
            
            if 'defaultCrypto' in data:
                self.default_crypto = str(data['defaultCrypto'])
            
            if 'timeFormat' in data:
                self.time_format = str(data['timeFormat'])
            
            if 'dateFormat' in data:
                self.date_format = str(data['dateFormat'])
            
            # Update JSON settings
            if 'notifications' in data and isinstance(data['notifications'], dict):
                self.notifications_json = json.dumps(data['notifications'])
            
            if 'security' in data and isinstance(data['security'], dict):
                self.security_json = json.dumps(data['security'])
            
            if 'trading' in data and isinstance(data['trading'], dict):
                self.trading_json = json.dumps(data['trading'])
            
            if 'display' in data and isinstance(data['display'], dict):
                self.display_json = json.dumps(data['display'])
            
            if 'privacy' in data and isinstance(data['privacy'], dict):
                self.privacy_json = json.dumps(data['privacy'])
            
            return True, None
        except Exception as e:
            return False, str(e)
    
    def __repr__(self):
        return f"UserSettings(User: {self.user_id}, Theme: {'Dark' if self.theme else 'Light'})"