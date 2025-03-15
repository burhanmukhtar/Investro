# app/models/trade_signal.py
from datetime import datetime
from app import db

class TradeSignal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    currency_pair = db.Column(db.String(20), nullable=False)  # e.g., BTC/USDT
    signal_type = db.Column(db.String(10), nullable=False)  # buy, sell
    entry_price = db.Column(db.Float, nullable=False)
    target_price = db.Column(db.Float, nullable=False)
    stop_loss = db.Column(db.Float, nullable=False)
    leverage = db.Column(db.Integer, default=1)
    description = db.Column(db.Text, nullable=True)
    expiry_time = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    result = db.Column(db.String(10), nullable=True)  # profit, loss, pending
    profit_percentage = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    positions = db.relationship('TradePosition', backref='signal', lazy=True)
    
    def __repr__(self):
        return f"TradeSignal(Pair: {self.currency_pair}, Type: {self.signal_type}, Active: {self.is_active})"

class TradePosition(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    signal_id = db.Column(db.Integer, db.ForeignKey('trade_signal.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    entry_price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='open')  # open, closed
    close_price = db.Column(db.Float, nullable=True)
    profit_loss = db.Column(db.Float, nullable=True)
    profit_loss_percentage = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    closed_at = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f"TradePosition(User: {self.user_id}, Signal: {self.signal_id}, Amount: {self.amount}, Status: {self.status})"