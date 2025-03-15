# app/services/auth_service.py
import random
import string
from datetime import datetime, timedelta
from app import db
from app.models.user import User
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from app.config import Config

def generate_otp():
    """Generate a 6-digit OTP."""
    return ''.join(random.choices(string.digits, k=6))

def send_otp_email(email, otp):
    """Send OTP via email."""
    try:
        # Setup email
        message = MIMEMultipart()
        message['From'] = Config.MAIL_USERNAME
        message['To'] = email
        message['Subject'] = 'Your Verification Code'
        
        # Email body
        body = f"""
        <html>
        <body>
            <h2>Verification Code</h2>
            <p>Your verification code is: <strong>{otp}</strong></p>
            <p>This code will expire in 10 minutes.</p>
            <p>If you did not request this code, please ignore this email.</p>
        </body>
        </html>
        """
        
        message.attach(MIMEText(body, 'html'))
        
        # Connect to SMTP server
        server = smtplib.SMTP(Config.MAIL_SERVER, Config.MAIL_PORT)
        if Config.MAIL_USE_TLS:
            server.starttls()
        
        # Login if credentials are provided
        if Config.MAIL_USERNAME and Config.MAIL_PASSWORD:
            server.login(Config.MAIL_USERNAME, Config.MAIL_PASSWORD)
        
        # Send email
        server.send_message(message)
        server.quit()
        
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def send_otp_sms(phone, otp):
    """Send OTP via SMS using a third-party service."""
    try:
        # This is a placeholder. You should integrate with an actual SMS service
        # such as Twilio, Nexmo, or any other SMS gateway
        
        # Example using requests to a hypothetical SMS API
        payload = {
            'phone': phone,
            'message': f'Your verification code is: {otp}. It will expire in 10 minutes.',
            'api_key': Config.SMS_API_KEY  # You would need to add this to your Config
        }
        
        # response = requests.post('https://sms-api-provider.com/send', json=payload)
        # return response.status_code == 200
        
        # For development, just print the OTP to console
        print(f"SMS OTP for {phone}: {otp}")
        return True
    except Exception as e:
        print(f"Error sending SMS: {e}")
        return False

def verify_otp(user_id, otp):
    """Verify the OTP for a user."""
    user = User.query.get(user_id)
    
    if not user:
        return False
    
    if user.otp == otp and datetime.utcnow() <= user.otp_expiry:
        user.otp = None
        user.otp_expiry = None
        db.session.commit()
        return True
    
    return False

def register_user(username, email, phone, password, referral_code=None):
    """Register a new user."""
    # Check if username, email, or phone already exists
    if User.query.filter_by(username=username).first():
        return None, "Username already exists."
    
    if User.query.filter_by(email=email).first():
        return None, "Email already registered."
    
    if User.query.filter_by(phone=phone).first():
        return None, "Phone number already registered."
    
    # Check referral code if provided
    referred_by = None
    if referral_code:
        referring_user = User.query.filter_by(referral_code=referral_code).first()
        if referring_user:
            referred_by = referral_code
        else:
            return None, "Invalid referral code."
    
    # Create new user
    user = User(username=username, email=email, phone=phone, password=password, referred_by=referred_by)
    db.session.add(user)
    db.session.commit()
    
    return user, "User registered successfully."