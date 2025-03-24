# app/routes/auth.py
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, session
from flask_login import login_user, current_user, logout_user, login_required
from app import db, bcrypt
from app.models.user import User
from app.services.auth_service import generate_otp, send_otp_email, verify_otp
from app.utils.validators import validate_email, validate_password, validate_phone

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('user.home'))
    
    if request.method == 'POST':
        data = request.form
        
        # Get email/username and password
        login_identifier = data.get('login_identifier')
        password = data.get('password')
        
        # Check if input is email or username
        if '@' in login_identifier:
            user = User.query.filter_by(email=login_identifier).first()
        else:
            user = User.query.filter_by(username=login_identifier).first()
        
        if user and user.check_password(password):
            # Generate OTP for verification
            otp = user.generate_otp()
            db.session.commit()
            
            # Send OTP via email only
            send_otp_email(user.email, otp)
            
            # Show loading indicator or message
            flash('Verification code has been sent to your email. Please check your inbox.', 'info')
            
            # Store user ID in session for OTP verification
            session['user_id_for_otp'] = user.id
            
            return redirect(url_for('auth.verify_otp', source='login'))
        else:
            flash('Login failed. Please check your email/username and password.', 'danger')
    
    return render_template('auth/login.html', title='Login')

@auth.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('user.home'))
    
    # Get referral code from query parameters
    referral_code = request.args.get('ref')
    
    if request.method == 'POST':
        data = request.form
        
        username = data.get('username')
        email = data.get('email')
        phone = data.get('phone')
        password = data.get('password')
        confirm_password = data.get('confirm_password')
        referral_code = data.get('referral_code')
        
        # Validate inputs
        if not validate_email(email):
            flash('Please enter a valid email address.', 'danger')
            return render_template('auth/signup.html', title='Sign Up', referral_code=referral_code)
        
        if not validate_phone(phone):
            flash('Please enter a valid phone number.', 'danger')
            return render_template('auth/signup.html', title='Sign Up', referral_code=referral_code)
        
        if not validate_password(password):
            flash('Password must be at least 8 characters and include a uppercase letter, a lowercase letter, and a number.', 'danger')
            return render_template('auth/signup.html', title='Sign Up', referral_code=referral_code)
        
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/signup.html', title='Sign Up', referral_code=referral_code)
        
        # Check if username, email, or phone already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            return render_template('auth/signup.html', title='Sign Up', referral_code=referral_code)
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return render_template('auth/signup.html', title='Sign Up', referral_code=referral_code)
        
        if User.query.filter_by(phone=phone).first():
            flash('Phone number already registered.', 'danger')
            return render_template('auth/signup.html', title='Sign Up', referral_code=referral_code)
        
        # Check referral code if provided
        referred_by = None
        if referral_code:
            referring_user = User.query.filter_by(referral_code=referral_code).first()
            if referring_user:
                referred_by = referral_code
            else:
                flash('Invalid referral code.', 'warning')
        
        # Create new user
        user = User(username=username, email=email, phone=phone, password=password, referred_by=referred_by)
        db.session.add(user)
        db.session.commit()
        
        # Generate OTP for verification
        otp = user.generate_otp()
        db.session.commit()
        
        # Send OTP via email
        send_otp_email(email, otp)
        
        flash('Verification code has been sent to your email. Please check your inbox.', 'info')
        
        # Store user ID in session for OTP verification
        session['user_id_for_otp'] = user.id
        
        return redirect(url_for('auth.verify_otp', source='signup'))
    
    return render_template('auth/signup.html', title='Sign Up', referral_code=referral_code)

@auth.route('/verify-otp/<source>', methods=['GET', 'POST'])
def verify_otp(source):
    if 'user_id_for_otp' not in session:
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id_for_otp']
    user = User.query.get(user_id)
    
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        otp = request.form.get('otp')
        
        if user.verify_otp(otp):
            db.session.commit()
            
            # Remove OTP session
            session.pop('user_id_for_otp', None)
            
            # If from signup, set user as verified
            if source == 'signup':
                user.is_verified = True
                db.session.commit()
            
            # Log in the user
            login_user(user)
            
            # Redirect based on source
            if source == 'signup':
                flash('Account created successfully!', 'success')
            else:
                flash('Logged in successfully!', 'success')
            
            return redirect(url_for('user.home'))
        else:
            flash('Invalid OTP. Please try again.', 'danger')
    
    return render_template('auth/verify_otp.html', title='Verify OTP', source=source)

@auth.route('/resend-otp', methods=['POST'])
def resend_otp():
    if 'user_id_for_otp' not in session:
        return jsonify({'success': False, 'message': 'Session expired.'}), 401
    
    user_id = session['user_id_for_otp']
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'success': False, 'message': 'User not found.'}), 404
    
    # Generate new OTP
    otp = user.generate_otp()
    db.session.commit()
    
    # Send OTP via email only
    send_otp_email(user.email, otp)
    
    return jsonify({'success': True, 'message': 'OTP has been resent to your email.'})

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@auth.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('user.home'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Generate OTP
            otp = user.generate_otp()
            db.session.commit()
            
            # Send OTP via email
            send_otp_email(email, otp)
            
            flash('Verification code has been sent to your email. Please check your inbox.', 'info')
            
            # Store user ID in session for password reset
            session['user_id_for_reset'] = user.id
            
            return redirect(url_for('auth.reset_password'))
        else:
            flash('Email not found.', 'danger')
    
    return render_template('auth/forgot_password.html', title='Forgot Password')

@auth.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if current_user.is_authenticated:
        return redirect(url_for('user.home'))
    
    if 'user_id_for_reset' not in session:
        return redirect(url_for('auth.forgot_password'))
    
    user_id = session['user_id_for_reset']
    user = User.query.get(user_id)
    
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('auth.forgot_password'))
    
    if request.method == 'POST':
        otp = request.form.get('otp')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if not user.verify_otp(otp):
            flash('Invalid OTP.', 'danger')
            return render_template('auth/reset_password.html', title='Reset Password')
        
        if not validate_password(new_password):
            flash('Password must be at least 8 characters and include a uppercase letter, a lowercase letter, and a number.', 'danger')
            return render_template('auth/reset_password.html', title='Reset Password')
        
        if new_password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/reset_password.html', title='Reset Password')
        
        # Set new password
        user.set_password(new_password)
        db.session.commit()
        
        # Remove reset session
        session.pop('user_id_for_reset', None)
        
        flash('Password has been reset successfully. You can now log in with your new password.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password.html', title='Reset Password')