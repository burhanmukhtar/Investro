# app/models/wallet.py
from datetime import datetime
from app import db

class Wallet(db.Model):
    __tablename__ = 'wallet'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    currency = db.Column(db.String(10), nullable=False)
    spot_balance = db.Column(db.Float, default=0.0)
    funding_balance = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Each user can have multiple wallet entries, one for each currency
    __table_args__ = (db.UniqueConstraint('user_id', 'currency'),)
    
    def __repr__(self):
        return f"Wallet(User ID: {self.user_id}, Currency: {self.currency}, Spot: {self.spot_balance}, Funding: {self.funding_balance})"