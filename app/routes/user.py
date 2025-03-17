# app/routes/user.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.user import User, VerificationDocument
from app.models.wallet import Wallet
from app.models.announcement import Announcement
from app.services.market_service import get_market_data, get_popular_coins, get_new_listings
import os
from werkzeug.utils import secure_filename
from app.config import Config
from app.utils.helpers import format_currency_amount
import requests

user = Blueprint('user', __name__)

@user.route('/home')
@login_required
def home():
    # Get announcements
    announcements = Announcement.query.filter_by(is_active=True).order_by(Announcement.priority.desc()).all()
    
    # Get popular coins and new listings
    popular_coins = get_popular_coins()
    new_listings = get_new_listings()
    
    # Get user's wallets
    wallets = Wallet.query.filter_by(user_id=current_user.id).all()
    
    return render_template('user/home.html', 
                          title='Home', 
                          announcements=announcements,
                          popular_coins=popular_coins,
                          new_listings=new_listings,
                          wallets=wallets)

@user.route('/market')
@login_required
def market():
    # Get market data
    market_data = get_market_data()
    
    return render_template('user/market.html', 
                          title='Market', 
                          market_data=market_data)

@user.route('/future')
@login_required
def future():
    # Default coin for the chart
    selected_coin = request.args.get('coin', 'BTC/USDT')
    
    # Get available coins for dropdown
    available_coins = get_market_data(limit=50)
    
    # Get user's positions
    positions = []  # TODO: Get user's positions from DB
    
    # Get user's open orders
    open_orders = []  # TODO: Get user's open orders from DB
    
    # Get user's order history
    order_history = []  # TODO: Get user's order history from DB
    
    # Get trade signals
    trade_signals = []  # TODO: Get active trade signals from DB
    
    return render_template('user/future.html', 
                          title='Futures', 
                          selected_coin=selected_coin,
                          available_coins=available_coins,
                          positions=positions,
                          open_orders=open_orders,
                          order_history=order_history,
                          trade_signals=trade_signals)

@user.route('/assets')
@login_required
def assets():
    # Get user's wallets
    spot_wallets = Wallet.query.filter_by(user_id=current_user.id).all()
    
    # Fetch real-time conversion rates using a free API
    # Using CoinGecko API which doesn't require API key for basic usage
    try:
        response = requests.get('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,binancecoin,ripple&vs_currencies=usd')
        if response.status_code == 200:
            api_rates = response.json()
            rates = {
                'BTC': api_rates['bitcoin']['usd'],
                'ETH': api_rates['ethereum']['usd'],
                'BNB': api_rates['binancecoin']['usd'],
                'XRP': api_rates['ripple']['usd'],
                'USDT': 1  # Assuming 1 USDT = 1 USD
            }
        else:
            # Fallback rates if API call fails
            rates = {
                'BTC': 60000,
                'ETH': 3000,
                'BNB': 500,
                'XRP': 0.5,
                'USDT': 1
            }
    except Exception as e:
        # Log the exception
        print(f"Error fetching rates: {str(e)}")
        # Fallback rates if API call fails
        rates = {
            'BTC': 60000,
            'ETH': 3000,
            'BNB': 500,
            'XRP': 0.5,
            'USDT': 1
        }
    
    # Calculate total balance in USDT
    total_spot_balance = 0
    total_funding_balance = 0
    
    for wallet in spot_wallets:
        # Convert each currency to USDT using rates
        rate = rates.get(wallet.currency, 1)
        total_spot_balance += wallet.spot_balance * rate
        total_funding_balance += wallet.funding_balance * rate
    
    # Calculate the actual total balance as the sum of both spot and funding
    total_balance = total_spot_balance + total_funding_balance
    
    return render_template('user/assets.html', 
                          title='Assets', 
                          spot_wallets=spot_wallets,
                          rates=rates,
                          total_spot_balance=format_currency_amount(total_spot_balance, 'USDT', 2),
                          total_funding_balance=format_currency_amount(total_funding_balance, 'USDT', 2),
                          total_balance=format_currency_amount(total_balance, 'USDT', 2),
                          format_currency_amount=format_currency_amount)
@user.route('/profile')
@login_required
def profile():
    return render_template('user/profile.html', title='Profile')

@user.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    if 'profile_picture' in request.files:
        file = request.files['profile_picture']
        if file.filename != '':
            # Validate file type
            allowed_extensions = {'png', 'jpg', 'jpeg'}
            if '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in allowed_extensions:
                # Save file
                filename = secure_filename(f"{current_user.id}_{file.filename}")
                filepath = os.path.join(Config.UPLOAD_FOLDER, 'profile_pictures', filename)
                
                # Make sure directory exists
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                
                file.save(filepath)
                
                # Update user's profile picture
                current_user.profile_image = filename
                db.session.commit()
                
                flash('Profile picture updated successfully!', 'success')
            else:
                flash('Invalid file format. Allowed formats: PNG, JPG, JPEG', 'danger')
    
    # Update profile information
    username = request.form.get('username')
    
    # Only allow changing username if not verified
    if username and username != current_user.username:
        if current_user.is_verified:
            flash('Cannot change username after verification.', 'warning')
        else:
            # Check if username is available
            if User.query.filter_by(username=username).first():
                flash('Username already taken.', 'danger')
            else:
                current_user.username = username
                db.session.commit()
                flash('Username updated successfully!', 'success')
    
    return redirect(url_for('user.profile'))

@user.route('/profile/change-password', methods=['POST'])
@login_required
def change_password():
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    if not current_user.check_password(current_password):
        flash('Current password is incorrect.', 'danger')
        return redirect(url_for('user.profile'))
    
    if new_password != confirm_password:
        flash('New passwords do not match.', 'danger')
        return redirect(url_for('user.profile'))
    
    # Set new password
    current_user.set_password(new_password)
    db.session.commit()
    
    flash('Password changed successfully!', 'success')
    return redirect(url_for('user.profile'))

@user.route('/profile/set-withdrawal-pin', methods=['POST'])
@login_required
def set_withdrawal_pin():
    pin = request.form.get('pin')
    confirm_pin = request.form.get('confirm_pin')
    
    if pin != confirm_pin:
        flash('PINs do not match.', 'danger')
        return redirect(url_for('user.profile'))
    
    if len(pin) != 6 or not pin.isdigit():
        flash('PIN must be a 6-digit number.', 'danger')
        return redirect(url_for('user.profile'))
    
    # Set withdrawal PIN
    current_user.set_withdrawal_pin(pin)
    db.session.commit()
    
    flash('Withdrawal PIN set successfully!', 'success')
    return redirect(url_for('user.profile'))

@user.route('/profile/verification', methods=['GET', 'POST'])
@login_required
def verification():
    if request.method == 'POST':
        document_type = request.form.get('document_type')
        
        if 'document_file' not in request.files:
            flash('No file part', 'danger')
            return redirect(url_for('user.profile'))
        
        file = request.files['document_file']
        
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(url_for('user.profile'))
        
        # Validate file type
        allowed_extensions = {'png', 'jpg', 'jpeg', 'pdf'}
        if '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in allowed_extensions:
            # Save file
            filename = secure_filename(f"{current_user.id}_{document_type}_{file.filename}")
            filepath = os.path.join(Config.UPLOAD_FOLDER, 'verification_documents', filename)
            
            # Make sure directory exists
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            file.save(filepath)
            
            # Create verification document record
            doc = VerificationDocument(
                user_id=current_user.id,
                document_type=document_type,
                document_path=filename
            )
            
            db.session.add(doc)
            
            # Update user's verification status
            current_user.verification_status = 'pending'
            
            db.session.commit()
            
            flash('Verification document submitted successfully!', 'success')
        else:
            flash('Invalid file format. Allowed formats: PNG, JPG, JPEG, PDF', 'danger')
    
    # Get user's verification documents
    verification_documents = VerificationDocument.query.filter_by(user_id=current_user.id).all()
    
    return render_template('user/verification.html', 
                          title='Verification', 
                          verification_documents=verification_documents)

@user.route('/transaction-history')
@login_required
def transaction_history():
    # TODO: Get user's transaction history
    transactions = []
    
    return render_template('user/transaction_history.html', 
                          title='Transaction History', 
                          transactions=transactions)

@user.route('/referral')
@login_required
def referral():
    # Get referred users
    referred_users = User.query.filter_by(referred_by=current_user.referral_code).all()
    
    # TODO: Get referral rewards
    referral_rewards = []
    
    return render_template('user/referral.html', 
                          title='Referral', 
                          referred_users=referred_users,
                          referral_rewards=referral_rewards)

@user.route('/support')
@login_required
def support():
    # TODO: Get user's support tickets
    support_tickets = []
    
    return render_template('user/support.html', 
                          title='Support', 
                          support_tickets=support_tickets)

@user.route('/about')
@login_required
def about():
    return render_template('user/about.html', title='About Us')

@user.route('/settings')
@login_required
def settings():
    return render_template('user/settings.html', title='Settings')