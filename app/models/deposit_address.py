# app/models/deposit_address.py
from datetime import datetime
from app import db

class DepositAddress(db.Model):
    """Model for storing deposit addresses for different cryptocurrencies and networks."""
    __tablename__ = 'deposit_address'
    
    id = db.Column(db.Integer, primary_key=True)
    currency = db.Column(db.String(10), nullable=False)  # BTC, USDT, etc.
    network = db.Column(db.String(10), nullable=False)  # TRC20, ERC20, BTC, etc.
    address = db.Column(db.String(255), nullable=False)  # The actual deposit address
    qr_code_path = db.Column(db.String(255), nullable=True)  # Path to custom QR code image
    is_active = db.Column(db.Boolean, default=True)  # Whether this address is currently in use
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Admin who created/updated this address
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship with User (admin)
    admin = db.relationship('User', foreign_keys=[created_by])
    
    # Unique constraint to ensure only one active address per currency/network
    __table_args__ = (db.UniqueConstraint('currency', 'network', name='unique_currency_network'),)
    
    def __repr__(self):
        return f"DepositAddress({self.currency} on {self.network}: {self.address})"