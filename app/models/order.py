# Add this to app/models/order.py
from datetime import datetime
from app import db

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    currency_pair = db.Column(db.String(20), nullable=False)  # e.g., BTC/USDT
    order_type = db.Column(db.String(20), nullable=False)  # limit, stop, stop-limit
    side = db.Column(db.String(10), nullable=False)  # buy, sell
    price = db.Column(db.Float, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    filled_amount = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='open')  # open, filled, canceled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    filled_at = db.Column(db.DateTime, nullable=True)
    
    # User relationship
    user = db.relationship('User', backref=db.backref('orders', lazy=True))
    
    def __repr__(self):
        return f"Order(ID: {self.id}, User: {self.user_id}, Pair: {self.currency_pair}, Type: {self.order_type}, Side: {self.side}, Status: {self.status})"