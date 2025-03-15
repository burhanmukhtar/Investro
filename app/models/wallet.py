# app/models/wallet.py
from datetime import datetime
from app import db

class Wallet(db.Model):
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

# app/models/transaction.py
from datetime import datetime
import uuid
from app import db

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)  # deposit, withdrawal, transfer, convert, pay
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, completed, failed, cancelled
    currency = db.Column(db.String(10), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    fee = db.Column(db.Float, default=0.0)
    from_wallet = db.Column(db.String(20), nullable=True)  # spot, funding, external
    to_wallet = db.Column(db.String(20), nullable=True)  # spot, funding, external
    address = db.Column(db.String(255), nullable=True)  # blockchain address or user ID for internal transfers
    blockchain_txid = db.Column(db.String(255), nullable=True)  # blockchain transaction ID
    chain = db.Column(db.String(10), nullable=True)  # TRC20, ERC20, etc.
    notes = db.Column(db.Text, nullable=True)
    admin_notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"Transaction(ID: {self.transaction_id}, Type: {self.transaction_type}, Amount: {self.amount} {self.currency}, Status: {self.status})"

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

# app/models/announcement.py
from datetime import datetime
from app import db

class Announcement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    priority = db.Column(db.Integer, default=0)  # Higher number = higher priority
    start_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    end_date = db.Column(db.DateTime, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"Announcement('{self.title}', Active: {self.is_active})"