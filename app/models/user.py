# app/models/user.py
from datetime import datetime, timedelta
import uuid
import random
import string
from app import db, bcrypt, login_manager
from flask_login import UserMixin

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    unique_id = db.Column(db.String(20), unique=True, nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    withdrawal_pin_hash = db.Column(db.String(128), nullable=True)
    profile_image = db.Column(db.String(255), default='default.jpg')
    is_verified = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)
    verification_status = db.Column(db.String(20), default='unverified')  # unverified, pending, approved, rejected
    referral_code = db.Column(db.String(10), unique=True, nullable=False)
    referred_by = db.Column(db.String(10), nullable=True)
    otp = db.Column(db.String(6), nullable=True)
    otp_expiry = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    wallets = db.relationship('Wallet', backref='user', lazy=True)
    transactions = db.relationship('Transaction', backref='user', lazy=True)
    trade_positions = db.relationship('TradePosition', backref='user', lazy=True)
    verification_documents = db.relationship('VerificationDocument', backref='user', lazy=True)
    
    def __init__(self, username, email, phone, password, referred_by=None):
        self.username = username
        self.email = email
        self.phone = phone
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
        self.referred_by = referred_by
        self.generate_unique_id()
        self.generate_referral_code()
    
    def generate_unique_id(self):
        # Generate a unique ID for user transfers and payments
        uid = 'U' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        while User.query.filter_by(unique_id=uid).first():
            uid = 'U' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        self.unique_id = uid
    
    def generate_referral_code(self):
        # Generate a unique referral code
        ref_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        while User.query.filter_by(referral_code=ref_code).first():
            ref_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        self.referral_code = ref_code
    
    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)
    
    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    
    def set_withdrawal_pin(self, pin):
        self.withdrawal_pin_hash = bcrypt.generate_password_hash(pin).decode('utf-8')
    
    def check_withdrawal_pin(self, pin):
        return bcrypt.check_password_hash(self.withdrawal_pin_hash, pin)
    
    def generate_otp(self):
        self.otp = ''.join(random.choices(string.digits, k=6))
        self.otp_expiry = datetime.utcnow() + timedelta(minutes=10)
        return self.otp
    
    def verify_otp(self, otp):
        if self.otp == otp and datetime.utcnow() <= self.otp_expiry:
            self.otp = None
            self.otp_expiry = None
            return True
        return False
    
    def __repr__(self):
        return f"User('{self.username}', '{self.email}')"

class VerificationDocument(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    document_type = db.Column(db.String(50), nullable=False)  # ID, passport, driver's license
    document_path = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    admin_notes = db.Column(db.Text, nullable=True)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f"VerificationDocument('{self.document_type}', '{self.status}')"