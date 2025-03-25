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
    
    # Separate email verification from KYC verification
    email_verified = db.Column(db.Boolean, default=False)
    is_verified = db.Column(db.Boolean, default=False)
    verification_status = db.Column(db.String(20), default='unverified')  # unverified, pending, approved, rejected
    
    referral_code = db.Column(db.String(10), unique=True, nullable=False)
    referred_by = db.Column(db.String(10), nullable=True)
    otp = db.Column(db.String(6), nullable=True)
    otp_expiry = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=False)
    
    # Relationships
    wallets = db.relationship('Wallet', backref='user', lazy=True)
    transactions = db.relationship('Transaction', backref='user', lazy=True)
    trade_positions = db.relationship('TradePosition', backref='user', lazy=True)
    verification_documents = db.relationship('VerificationDocument', backref='user', lazy=True)
    
    # Add relationship for referred users
    referred_users = db.relationship(
        'User', 
        primaryjoin="User.referral_code==User.referred_by",
        foreign_keys="User.referred_by",
        backref=db.backref('referrer', uselist=False, remote_side="User.referral_code")
    )
    
    def __init__(self, username, email, phone, password, referred_by=None):
        self.username = username
        self.email = email
        self.phone = phone
        
        # Check if password is already hashed
        if password.startswith('$2b$') or password.startswith('$2a$'):
            self.password_hash = password
        else:
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
    
    def has_completed_kyc(self):
        """Check if the user has completed KYC verification"""
        return self.is_verified and self.verification_status == 'approved'
    
    def get_total_deposits(self):
        """
        Get total deposits made by the user in USDT.
        """
        from app.models.transaction import Transaction
        
        deposits = Transaction.query.filter_by(
            user_id=self.id,
            transaction_type='deposit',
            status='completed'
        ).all()
        
        total_amount = 0
        for deposit in deposits:
            # Sum all deposits in USDT or convert to USDT equivalent
            if deposit.currency == 'USDT':
                total_amount += deposit.amount
            else:
                from app.services.wallet_service import get_conversion_rate
                try:
                    rate = get_conversion_rate(deposit.currency, 'USDT')
                    total_amount += deposit.amount * rate
                except:
                    total_amount += deposit.amount
        
        return total_amount
    
    def __repr__(self):
        return f"User('{self.username}', '{self.email}')"

class PendingUser(db.Model):
    """Model for users that have started registration but not verified OTP yet"""
    id = db.Column(db.String(36), primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    referred_by = db.Column(db.String(10), nullable=True)
    otp = db.Column(db.String(6), nullable=True)
    otp_expiry = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
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
        return f"PendingUser('{self.username}', '{self.email}')"


class VerificationDocument(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    document_type = db.Column(db.String(50), nullable=False)  # ID, passport, driver's license
    document_path = db.Column(db.String(255), nullable=False)
    document_side = db.Column(db.String(10), default='front')  # front, back, selfie
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    admin_notes = db.Column(db.Text, nullable=True)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f"VerificationDocument('{self.document_type}', '{self.status}')"


class ReferralReward(db.Model):
    """Model for tracking referral rewards."""
    
    id = db.Column(db.Integer, primary_key=True)
    referrer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    referred_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), nullable=False)
    status = db.Column(db.String(20), default='completed')  # pending, completed, failed
    transaction_id = db.Column(db.Integer, db.ForeignKey('transaction.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    referrer = db.relationship('User', foreign_keys=[referrer_id], backref='given_rewards')
    referred = db.relationship('User', foreign_keys=[referred_id], backref='received_rewards')
    transaction = db.relationship('Transaction', backref='referral_reward')
    
    @property
    def referred_username(self):
        """Get the username of the referred user."""
        user = User.query.get(self.referred_id)
        return user.username if user else "Unknown"