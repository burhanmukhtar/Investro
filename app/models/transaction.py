# app/models/transaction.py
from datetime import datetime
import uuid
from app import db

class Transaction(db.Model):
    __tablename__ = 'transaction'
    __table_args__ = {'extend_existing': True}  # Add this line
    
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