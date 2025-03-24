# app/routes/user.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.user import User, VerificationDocument
from app.models.wallet import Wallet
from app.models.announcement import Announcement
from app.services.market_service import (
    get_market_data, 
    get_popular_coins_service as get_popular_coins, 
    get_new_listings_service as get_new_listings
)
import os
from werkzeug.utils import secure_filename
from app.config import Config
from app.utils.helpers import format_currency_amount
import logging
from datetime import datetime, timedelta
from app.models.transaction import Transaction


logger = logging.getLogger(__name__)
user = Blueprint('user', __name__)

@user.route('/home')
@login_required
def home():
    """
    User home page with announcements and market overview
    """
    try:
        # Get active announcements
        announcements = Announcement.query.filter(
            Announcement.is_active == True,
            (Announcement.expiry_date.is_(None) | (Announcement.expiry_date >= datetime.utcnow()))
        ).order_by(Announcement.priority.desc(), Announcement.created_at.desc()).all()
        
        # Get popular coins and new listings
        try:
            popular_coins = get_popular_coins()
        except Exception as e:
            logger.error(f"Error getting popular coins: {str(e)}")
            popular_coins = []
            
        try:
            new_listings = get_new_listings()
        except Exception as e:
            logger.error(f"Error getting new listings: {str(e)}")
            new_listings = []
        
        # Get user's wallets
        wallets = Wallet.query.filter_by(user_id=current_user.id).all()
        
        return render_template('user/home.html', 
                              title='Home', 
                              announcements=announcements,
                              popular_coins=popular_coins,
                              new_listings=new_listings,
                              wallets=wallets)
    except Exception as e:
        logger.error(f"Error loading home page: {str(e)}")
        flash("Error loading dashboard. Please try again later.", "danger")
        # Fallback to a simpler page if needed
        return render_template('user/home_basic.html', title='Home')

@user.route('/market')
@login_required
def market():
    """
    Market overview page
    """
    try:
        # Get market data
        market_data = get_market_data()
        
        return render_template('user/market.html', 
                              title='Market', 
                              market_data=market_data)
    except Exception as e:
        logger.error(f"Error loading market page: {str(e)}")
        flash("Error loading market data. Please try again later.", "danger")
        return redirect(url_for('user.home'))

@user.route('/future')
@login_required
def future():
    """
    Futures trading page
    """
    try:
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
    except Exception as e:
        logger.error(f"Error loading futures page: {str(e)}")
        flash("Error loading futures data. Please try again later.", "danger")
        return redirect(url_for('user.home'))

@user.route('/assets', methods=['GET'])
@login_required
def assets():
    """
    Display user's asset page with portfolio information
    """
    try:
        # Get user's wallets
        spot_wallets = Wallet.query.filter_by(user_id=current_user.id).all()
        
        # Fetch real-time conversion rates using CoinGecko API
        rates = {}
        try:
            from app.utils.crypto_api import get_coin_details
            
            # Get USDT rates for main cryptocurrencies
            for currency in ['BTC', 'ETH', 'BNB', 'XRP', 'USDT']:
                if currency == 'USDT':
                    rates['USDT'] = 1.0  # 1 USDT = 1 USD
                    continue
                
                try:
                    # Get coin details which includes current price in USD
                    coin_data = get_coin_details(currency)
                    
                    # Store the USD price
                    if coin_data and 'current_price' in coin_data:
                        rates[currency] = coin_data['current_price']
                except Exception as e:
                    logger.error(f"Error fetching rate for {currency}: {str(e)}")
                    # Use fallback rates if API call fails for a specific coin
                    fallback_rates = {
                        'BTC': 60000,
                        'ETH': 3000,
                        'BNB': 500,
                        'XRP': 0.5
                    }
                    rates[currency] = fallback_rates.get(currency, 1.0)
                    
        except Exception as e:
            logger.error(f"Error fetching all rates: {str(e)}")
            # Fallback rates if all API calls fail
            rates = {
                'BTC': 60000,
                'ETH': 3000,
                'BNB': 500,
                'XRP': 0.5,
                'USDT': 1.0
            }
        
        # Calculate total balance in USDT
        total_spot_balance = 0
        total_funding_balance = 0
        
        for wallet in spot_wallets:
            # Convert each currency to USDT using rates
            rate = rates.get(wallet.currency, 1.0)
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
                              
    except Exception as e:
        logger.error(f"Error loading assets page: {str(e)}")
        flash(f"Error loading assets: {str(e)}", "danger")
        return redirect(url_for('user.home'))

@user.route('/api/portfolio', methods=['GET'])
@login_required
def get_portfolio_data():
    """
    Get user portfolio data as JSON for API requests
    """
    try:
        # Get user's wallets
        wallets = Wallet.query.filter_by(user_id=current_user.id).all()
        
        # Get real-time rates
        try:
            from app.utils.crypto_api import get_coin_details
            
            # Get USDT rates for main cryptocurrencies
            rates = {}
            for wallet in wallets:
                currency = wallet.currency
                
                if currency == 'USDT':
                    rates['USDT'] = 1.0  # 1 USDT = 1 USD
                    continue
                    
                if currency in rates:
                    continue
                
                try:
                    # Get coin details which includes current price in USD
                    coin_data = get_coin_details(currency)
                    
                    # Store the USD price
                    if coin_data and 'current_price' in coin_data:
                        rates[currency] = coin_data['current_price']
                except Exception as e:
                    logger.error(f"Error fetching rate for {currency}: {str(e)}")
                    # Use fallback value
                    rates[currency] = 0.0
        except Exception as e:
            logger.error(f"Error fetching rates: {str(e)}")
            rates = {wallet.currency: 0.0 for wallet in wallets}
            rates['USDT'] = 1.0  # Always ensure USDT has a value
        
        # Prepare portfolio data
        portfolio = {
            'spot': {},
            'funding': {},
            'total_spot_value': 0,
            'total_funding_value': 0,
            'total_value': 0
        }
        
        # Process each wallet
        for wallet in wallets:
            # Skip empty wallets
            if wallet.spot_balance == 0 and wallet.funding_balance == 0:
                continue
            
            # Get equivalent value in USDT
            rate = rates.get(wallet.currency, 0)
            
            spot_value = wallet.spot_balance * rate
            funding_value = wallet.funding_balance * rate
            
            portfolio['spot'][wallet.currency] = {
                'balance': wallet.spot_balance,
                'value_usdt': spot_value
            }
            
            portfolio['funding'][wallet.currency] = {
                'balance': wallet.funding_balance,
                'value_usdt': funding_value
            }
            
            portfolio['total_spot_value'] += spot_value
            portfolio['total_funding_value'] += funding_value
        
        portfolio['total_value'] = portfolio['total_spot_value'] + portfolio['total_funding_value']
        
        return jsonify({
            'success': True,
            'portfolio': portfolio,
            'rates': rates
        })
        
    except Exception as e:
        logger.error(f"Error getting portfolio data: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error getting portfolio data: {str(e)}"
        }), 500

@user.route('/profile')
@login_required
def profile():
    """
    User profile page
    """
    try:
        return render_template('user/profile.html', title='Profile')
    except Exception as e:
        logger.error(f"Error loading profile page: {str(e)}")
        flash("Error loading profile. Please try again later.", "danger")
        return redirect(url_for('user.home'))

@user.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    """
    Update user profile information
    """
    try:
        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file.filename != '':
                # Validate file type
                allowed_extensions = {'png', 'jpg', 'jpeg'}
                if '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in allowed_extensions:
                    # Save file
                    filename = secure_filename(f"{current_user.id}_{file.filename}")
                    
                    # Make sure directory exists
                    upload_dir = os.path.join(Config.UPLOAD_FOLDER, 'profile_pictures')
                    os.makedirs(upload_dir, exist_ok=True)
                    
                    filepath = os.path.join(upload_dir, filename)
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
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating profile: {str(e)}")
        flash(f"Error updating profile: {str(e)}", "danger")
        return redirect(url_for('user.profile'))

@user.route('/profile/change-password', methods=['POST'])
@login_required
def change_password():
    """
    Change user password
    """
    try:
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
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error changing password: {str(e)}")
        flash(f"Error changing password: {str(e)}", "danger")
        return redirect(url_for('user.profile'))

@user.route('/profile/set-withdrawal-pin', methods=['POST'])
@login_required
def set_withdrawal_pin():
    """
    Set withdrawal PIN for secure withdrawals
    """
    try:
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
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error setting withdrawal PIN: {str(e)}")
        flash(f"Error setting withdrawal PIN: {str(e)}", "danger")
        return redirect(url_for('user.profile'))

@user.route('/profile/verification', methods=['GET', 'POST'])
@login_required
def verification():
    """
    Handle KYC verification document submission
    """
    try:
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
                
                # Make sure directory exists
                upload_dir = os.path.join(Config.UPLOAD_FOLDER, 'verification_documents')
                os.makedirs(upload_dir, exist_ok=True)
                
                filepath = os.path.join(upload_dir, filename)
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
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error processing verification: {str(e)}")
        flash(f"Error processing verification: {str(e)}", "danger")
        return redirect(url_for('user.profile'))

@user.route('/transaction-history')
@login_required
def transaction_history():
    """
    View transaction history page
    """
    try:
        # We're using client-side JavaScript to load transaction data, 
        # so we just render the template and the data is fetched via API
        return render_template('user/transaction_history.html', title='Transaction History')
    except Exception as e:
        logger.error(f"Error loading transaction history page: {str(e)}")
        flash("Error loading transaction history. Please try again later.", "danger")
        return redirect(url_for('user.home'))

@user.route('/api/transactions', methods=['GET'])
@login_required
def api_transactions():
    """
    API endpoint for transaction history
    """
    try:
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        transaction_type = request.args.get('type')
        status = request.args.get('status')
        currency = request.args.get('currency')
        date_range = request.args.get('date_range')
        sort_field = request.args.get('sort_field', 'created_at')
        sort_dir = request.args.get('sort_dir', 'desc')
        
        # Query for transactions with optional filtering
        query = Transaction.query.filter_by(user_id=current_user.id)
        
        if transaction_type and transaction_type != 'all':
            query = query.filter_by(transaction_type=transaction_type)
            
        if status and status != 'all':
            query = query.filter_by(status=status)
            
        if currency and currency != 'all':
            query = query.filter_by(currency=currency)
            
        if date_range and date_range != 'all':
            today = datetime.now().date()
            if date_range == 'today':
                start_date = today
            elif date_range == 'week':
                start_date = today - timedelta(days=7)
            elif date_range == 'month':
                start_date = today - timedelta(days=30)
            elif date_range == 'quarter':
                start_date = today - timedelta(days=90)
            elif date_range == 'year':
                start_date = today - timedelta(days=365)
            else:
                start_date = None
            
            if start_date:
                query = query.filter(Transaction.created_at >= datetime.combine(start_date, datetime.min.time()))
        
        # Apply sorting
        if sort_field == 'date':
            sort_field = 'created_at'
        elif sort_field == 'type':
            sort_field = 'transaction_type'
        elif sort_field == 'amount':
            sort_field = 'amount'
        
        if sort_dir == 'asc':
            query = query.order_by(getattr(Transaction, sort_field).asc())
        else:
            query = query.order_by(getattr(Transaction, sort_field).desc())
            
        # Apply pagination and get transactions
        pagination = query.paginate(page=page, per_page=per_page)
        transactions = pagination.items
        
        # Format transaction data for API response
        transaction_data = []
        for tx in transactions:
            transaction_data.append({
                'id': tx.id,
                'transaction_id': tx.transaction_id,
                'type': tx.transaction_type,
                'status': tx.status,
                'currency': tx.currency,
                'amount': tx.amount,
                'fee': tx.fee,
                'from_wallet': tx.from_wallet,
                'to_wallet': tx.to_wallet,
                'address': tx.address,
                'blockchain_txid': tx.blockchain_txid,
                'chain': tx.chain,
                'notes': tx.notes,
                'created_at': tx.created_at.isoformat() if tx.created_at else None,
                'updated_at': tx.updated_at.isoformat() if tx.updated_at else None
            })
        
        return jsonify({
            'success': True,
            'transactions': transaction_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total_items': pagination.total,
                'total_pages': pagination.pages
            }
        })
    except Exception as e:
        logger.error(f"Error fetching transaction data: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error fetching transaction data: {str(e)}"
        }), 500
    
@user.route('/api/transactions/<int:transaction_id>', methods=['GET'])
@login_required
def api_transaction_detail(transaction_id):
    """
    API endpoint for transaction details
    """
    try:
        # Ensure user can only access their own transactions
        transaction = Transaction.query.filter_by(
            id=transaction_id, 
            user_id=current_user.id
        ).first()
        
        if not transaction:
            return jsonify({
                'success': False,
                'message': 'Transaction not found or unauthorized access'
            }), 404
        
        # Format transaction data for API response
        transaction_data = {
            'id': transaction.id,
            'transaction_id': transaction.transaction_id,
            'type': transaction.transaction_type,
            'status': transaction.status,
            'currency': transaction.currency,
            'amount': transaction.amount,
            'fee': transaction.fee,
            'from_wallet': transaction.from_wallet,
            'to_wallet': transaction.to_wallet,
            'address': transaction.address,
            'blockchain_txid': transaction.blockchain_txid,
            'chain': transaction.chain,
            'notes': transaction.notes,
            'admin_notes': transaction.admin_notes,
            'created_at': transaction.created_at.isoformat() if transaction.created_at else None,
            'updated_at': transaction.updated_at.isoformat() if transaction.updated_at else None
        }
        
        return jsonify({
            'success': True,
            'transaction': transaction_data
        })
    except Exception as e:
        logger.error(f"Error fetching transaction details: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error fetching transaction details: {str(e)}"
        }), 500

@user.route('/api/transactions/export', methods=['GET'])
@login_required
def export_transactions():
    """
    Export transactions to CSV
    """
    try:
        import csv
        from io import StringIO
        from flask import Response
        
        # Get filter parameters
        transaction_type = request.args.get('type')
        status = request.args.get('status')
        currency = request.args.get('currency')
        date_range = request.args.get('date_range')
        
        # Query for transactions with optional filtering
        query = Transaction.query.filter_by(user_id=current_user.id)
        
        if transaction_type and transaction_type != 'all':
            query = query.filter_by(transaction_type=transaction_type)
            
        if status and status != 'all':
            query = query.filter_by(status=status)
            
        if currency and currency != 'all':
            query = query.filter_by(currency=currency)
            
        if date_range and date_range != 'all':
            today = datetime.now().date()
            if date_range == 'today':
                start_date = today
            elif date_range == 'week':
                start_date = today - timedelta(days=7)
            elif date_range == 'month':
                start_date = today - timedelta(days=30)
            elif date_range == 'quarter':
                start_date = today - timedelta(days=90)
            elif date_range == 'year':
                start_date = today - timedelta(days=365)
            else:
                start_date = None
            
            if start_date:
                query = query.filter(Transaction.created_at >= datetime.combine(start_date, datetime.min.time()))
        
        # Order by created_at
        transactions = query.order_by(Transaction.created_at.desc()).all()
        
        # Create CSV file
        csv_data = StringIO()
        fieldnames = [
            'Transaction ID', 'Type', 'Status', 'Currency', 'Amount', 'Fee', 
            'From', 'To', 'Address', 'Blockchain TxID', 'Chain', 'Notes', 'Date'
        ]
        
        writer = csv.DictWriter(csv_data, fieldnames=fieldnames)
        writer.writeheader()
        
        for tx in transactions:
            writer.writerow({
                'Transaction ID': tx.transaction_id,
                'Type': tx.transaction_type,
                'Status': tx.status,
                'Currency': tx.currency,
                'Amount': tx.amount,
                'Fee': tx.fee or 0,
                'From': tx.from_wallet or '',
                'To': tx.to_wallet or '',
                'Address': tx.address or '',
                'Blockchain TxID': tx.blockchain_txid or '',
                'Chain': tx.chain or '',
                'Notes': tx.notes or '',
                'Date': tx.created_at.strftime('%Y-%m-%d %H:%M:%S') if tx.created_at else ''
            })
        
        # Create response
        response = Response(
            csv_data.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=transaction_history.csv'}
        )
        
        return response
    except Exception as e:
        logger.error(f"Error exporting transactions: {str(e)}")
        flash(f"Error exporting transactions: {str(e)}", "danger")
        return redirect(url_for('user.transaction_history'))    

@user.route('/referral')
@login_required
def referral():
    """
    Referral program page showing referrals and rewards
    """
    try:
        # Get referred users
        referred_users = User.query.filter_by(referred_by=current_user.referral_code).all()
        
        # Import referral service functions
        from app.services.referral_service import (
            is_eligible_for_referral_reward, 
            process_referral_reward,
            get_reward_by_referred_user
        )
        
        # Get referral rewards
        from app.models.user import ReferralReward
        referral_rewards = ReferralReward.query.filter_by(referrer_id=current_user.id).order_by(ReferralReward.created_at.desc()).all()
        
        # Check for newly eligible referrals and process rewards
        for referred_user in referred_users:
            if is_eligible_for_referral_reward(referred_user.id):
                success, message = process_referral_reward(referred_user.id)
                if success:
                    logger.info(f"Processed referral reward for {referred_user.username}")
                else:
                    logger.warning(f"Failed to process referral reward for {referred_user.username}: {message}")
        
        # Refresh the rewards list after processing
        referral_rewards = ReferralReward.query.filter_by(referrer_id=current_user.id).order_by(ReferralReward.created_at.desc()).all()
        
        return render_template('user/referral.html', 
                              title='Referral Program', 
                              referred_users=referred_users,
                              referral_rewards=referral_rewards,
                              get_reward_by_referred_user=get_reward_by_referred_user)
    except Exception as e:
        logger.error(f"Error loading referral page: {str(e)}")
        flash("Error loading referral data. Please try again later.", "danger")
        return redirect(url_for('user.home'))

@user.route('/support')
@login_required
def support():
    """
    Support page
    """
    try:
        # TODO: Get user's support tickets
        support_tickets = []
        
        return render_template('user/support.html', 
                              title='Support', 
                              support_tickets=support_tickets)
    except Exception as e:
        logger.error(f"Error loading support page: {str(e)}")
        flash("Error loading support page. Please try again later.", "danger")
        return redirect(url_for('user.home'))

@user.route('/about')
@login_required
def about():
    """
    About page
    """
    try:
        return render_template('user/about.html', title='About Us')
    except Exception as e:
        logger.error(f"Error loading about page: {str(e)}")
        flash("Error loading about page. Please try again later.", "danger")
        return redirect(url_for('user.home'))

@user.route('/settings')
@login_required
def settings():
    """
    User settings page
    """
    try:
        return render_template('user/settings.html', title='Settings')
    except Exception as e:
        logger.error(f"Error loading settings page: {str(e)}")
        flash("Error loading settings page. Please try again later.", "danger")
        return redirect(url_for('user.home'))