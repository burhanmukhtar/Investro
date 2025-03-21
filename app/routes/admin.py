# app/routes/admin.py
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
from app.models.user import User, VerificationDocument
from app.models.wallet import Wallet
from app.models.transaction import Transaction
from app.models.trade_signal import TradeSignal, TradePosition
from app.models.announcement import Announcement
from app.services.market_service import get_current_price
from datetime import datetime, timedelta
from functools import wraps

admin = Blueprint('admin', __name__)

# Admin required decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Access denied. Admin privileges required.', 'danger')
            return redirect(url_for('user.home'))
        return f(*args, **kwargs)
    return decorated_function

@admin.route('/dashboard')
@login_required
@admin_required
def dashboard():
    # Get stats for dashboard
    total_users = User.query.count()
    verified_users = User.query.filter_by(is_verified=True).count()
    pending_verifications = VerificationDocument.query.filter_by(status='pending').count()
    
    # Get transaction stats
    pending_deposits = Transaction.query.filter_by(transaction_type='deposit', status='pending').count()
    pending_withdrawals = Transaction.query.filter_by(transaction_type='withdrawal', status='pending').count()
    
    # Get active trade signals
    active_signals = TradeSignal.query.filter_by(is_active=True).count()
    
    # Get recent user registrations
    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()
    
    # Get recent transactions
    recent_transactions = Transaction.query.order_by(Transaction.created_at.desc()).limit(10).all()
    
    return render_template('admin/dashboard.html', 
                          title='Admin Dashboard',
                          total_users=total_users,
                          verified_users=verified_users,
                          pending_verifications=pending_verifications,
                          pending_deposits=pending_deposits,
                          pending_withdrawals=pending_withdrawals,
                          active_signals=active_signals,
                          recent_users=recent_users,
                          recent_transactions=recent_transactions)

@admin.route('/users')
@login_required
@admin_required
def users():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    # Search for users
    if search:
        users = User.query.filter(
            (User.username.like(f'%{search}%')) |
            (User.email.like(f'%{search}%')) |
            (User.unique_id.like(f'%{search}%'))
        ).paginate(page=page, per_page=20)
    else:
        users = User.query.paginate(page=page, per_page=20)
    
    return render_template('admin/users.html', 
                          title='User Management',
                          users=users,
                          search=search)

@admin.route('/user/<int:user_id>')
@login_required
@admin_required
def user_detail(user_id):
    user = User.query.get_or_404(user_id)
    
    # Get user's wallets
    wallets = Wallet.query.filter_by(user_id=user_id).all()
    
    # Get user's transactions
    transactions = Transaction.query.filter_by(user_id=user_id).order_by(Transaction.created_at.desc()).limit(20).all()
    
    # Get user's verification documents
    verification_documents = VerificationDocument.query.filter_by(user_id=user_id).all()
    
    return render_template('admin/user_detail.html', 
                          title=f'User: {user.username}',
                          user=user,
                          wallets=wallets,
                          transactions=transactions,
                          verification_documents=verification_documents)

@admin.route('/toggle-admin/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def toggle_admin(user_id):
    user = User.query.get_or_404(user_id)
    
    # Only super admin can toggle admin status
    if not current_user.id == 1:  # Assuming user ID 1 is super admin
        return jsonify({'success': False, 'message': 'Only super admin can perform this action.'})
    
    user.is_admin = not user.is_admin
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f"Admin status for {user.username} {'enabled' if user.is_admin else 'disabled'}.",
        'is_admin': user.is_admin
    })

@admin.route('/verifications')
@login_required
@admin_required
def verifications():
    status = request.args.get('status', 'pending')
    page = request.args.get('page', 1, type=int)
    
    # Get verification documents by status
    verifications = VerificationDocument.query.filter_by(status=status).order_by(VerificationDocument.submitted_at.desc()).paginate(page=page, per_page=20)
    
    return render_template('admin/verifications.html', 
                          title='Verification Requests',
                          verifications=verifications,
                          status=status)

@admin.route('/verify-document/<int:doc_id>', methods=['POST'])
@login_required
@admin_required
def verify_document(doc_id):
    document = VerificationDocument.query.get_or_404(doc_id)
    
    # Check if the request is JSON or form data
    if request.is_json:
        data = request.json
    else:
        data = request.form
    
    action = data.get('action')
    admin_notes = data.get('admin_notes', '')
    
    if action not in ['approve', 'reject']:
        return jsonify({'success': False, 'message': 'Invalid action.'})
    
    # Update document status
    document.status = 'approved' if action == 'approve' else 'rejected'
    document.admin_notes = admin_notes
    document.reviewed_at = datetime.utcnow()
    
    # Update user verification status if approved
    user = User.query.get(document.user_id)
    if action == 'approve':
        user.verification_status = 'approved'
        user.is_verified = True
    else:
        user.verification_status = 'rejected'
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f"Document {document.status}.",
        'status': document.status
    })

@admin.route('/deposits')
@login_required
@admin_required
def deposits():
    status = request.args.get('status', 'pending')
    page = request.args.get('page', 1, type=int)
    
    # Get deposit transactions by status
    deposits = Transaction.query.filter_by(transaction_type='deposit', status=status).order_by(Transaction.created_at.desc()).paginate(page=page, per_page=20)
    
    return render_template('admin/deposits.html', 
                          title='Deposit Management',
                          deposits=deposits,
                          status=status)

@admin.route('/process-deposit/<int:tx_id>', methods=['POST'])
@login_required
@admin_required
def process_deposit(tx_id):
    transaction = Transaction.query.get_or_404(tx_id)
    
    # Check if the request is JSON or form data
    if request.is_json:
        data = request.json
    else:
        data = request.form
    
    action = data.get('action')
    admin_notes = data.get('admin_notes', '')
    
    if action not in ['approve', 'reject']:
        return jsonify({'success': False, 'message': 'Invalid action.'})
    
    # Update transaction status
    transaction.status = 'completed' if action == 'approve' else 'failed'
    transaction.admin_notes = admin_notes
    transaction.updated_at = datetime.utcnow()
    
    # If approved, add funds to user's wallet
    if action == 'approve':
        wallet = Wallet.query.filter_by(user_id=transaction.user_id, currency=transaction.currency).first()
        
        if not wallet:
            wallet = Wallet(user_id=transaction.user_id, currency=transaction.currency, spot_balance=0)
            db.session.add(wallet)
        
        wallet.spot_balance += transaction.amount
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f"Deposit {transaction.status}.",
        'status': transaction.status
    })


@admin.route('/withdrawals')
@login_required
@admin_required
def withdrawals():
    status = request.args.get('status', 'pending')
    page = request.args.get('page', 1, type=int)
    
    # Get withdrawal transactions by status
    withdrawals = Transaction.query.filter_by(transaction_type='withdrawal', status=status).order_by(Transaction.created_at.desc()).paginate(page=page, per_page=20)
    
    return render_template('admin/withdrawals.html', 
                          title='Withdrawal Management',
                          withdrawals=withdrawals,
                          status=status)

@admin.route('/process-withdrawal/<int:tx_id>', methods=['POST'])
@login_required
@admin_required
def process_withdrawal(tx_id):
    transaction = Transaction.query.get_or_404(tx_id)
    
    # Check if the request is JSON or form data
    if request.is_json:
        data = request.json
    else:
        data = request.form
    
    action = data.get('action')
    blockchain_txid = data.get('blockchain_txid', '')
    admin_notes = data.get('admin_notes', '')
    
    if action not in ['approve', 'reject']:
        return jsonify({'success': False, 'message': 'Invalid action.'})
    
    # Update transaction status
    transaction.status = 'completed' if action == 'approve' else 'failed'
    transaction.blockchain_txid = blockchain_txid if action == 'approve' else None
    transaction.admin_notes = admin_notes
    transaction.updated_at = datetime.utcnow()
    
    # If rejected, return funds to user's wallet
    if action == 'reject':
        wallet = Wallet.query.filter_by(user_id=transaction.user_id, currency=transaction.currency).first()
        
        if wallet:
            wallet.spot_balance += transaction.amount + transaction.fee
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f"Withdrawal {transaction.status}.",
        'status': transaction.status
    })


@admin.route('/trade-signals')
@login_required
@admin_required
def trade_signals():
    status = request.args.get('status', 'active')
    page = request.args.get('page', 1, type=int)
    
    # Get trade signals by status
    if status == 'active':
        signals = TradeSignal.query.filter_by(is_active=True).order_by(TradeSignal.created_at.desc()).paginate(page=page, per_page=20)
    elif status == 'expired':
        signals = TradeSignal.query.filter_by(is_active=False).order_by(TradeSignal.created_at.desc()).paginate(page=page, per_page=20)
    else:
        signals = TradeSignal.query.order_by(TradeSignal.created_at.desc()).paginate(page=page, per_page=20)
    
    return render_template('admin/trade_signals.html', 
                          title='Trade Signals Management',
                          signals=signals,
                          status=status)

@admin.route('/create-signal', methods=['GET', 'POST'])
@login_required
@admin_required
def create_signal():
    if request.method == 'POST':
        currency_pair = request.form.get('currency_pair')
        signal_type = request.form.get('signal_type')
        entry_price = request.form.get('entry_price')
        target_price = request.form.get('target_price')
        stop_loss = request.form.get('stop_loss')
        leverage = request.form.get('leverage', 1)
        description = request.form.get('description', '')
        expiry_hours = request.form.get('expiry_hours', 24)
        
        # Validate input
        try:
            entry_price = float(entry_price)
            target_price = float(target_price)
            stop_loss = float(stop_loss)
            leverage = int(leverage)
            expiry_hours = int(expiry_hours)
        except ValueError:
            flash('Invalid input. Please check your values.', 'danger')
            return redirect(url_for('admin.create_signal'))
        
        # Create new trade signal
        signal = TradeSignal(
            admin_id=current_user.id,
            currency_pair=currency_pair,
            signal_type=signal_type,
            entry_price=entry_price,
            target_price=target_price,
            stop_loss=stop_loss,
            leverage=leverage,
            description=description,
            expiry_time=datetime.utcnow() + timedelta(hours=expiry_hours)
        )
        
        db.session.add(signal)
        db.session.commit()
        
        flash('Trade signal created successfully!', 'success')
        return redirect(url_for('admin.trade_signals'))
    
    # Get available currency pairs
    currency_pairs = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'XRP/USDT']  # TODO: Get from API
    
    return render_template('admin/create_signal.html', 
                          title='Create Trade Signal',
                          currency_pairs=currency_pairs)

@admin.route('/update-signal/<int:signal_id>', methods=['POST'])
@login_required
@admin_required
def update_signal(signal_id):
    signal = TradeSignal.query.get_or_404(signal_id)
    
    # Check if the request is JSON or form data
    if request.is_json:
        data = request.json
    else:
        data = request.form
    
    action = data.get('action')
    
    if action == 'deactivate':
        signal.is_active = False
        db.session.commit()
        return jsonify({'success': True, 'message': 'Signal deactivated.'})
    
    elif action == 'update_result':
        result = data.get('result')
        profit_percentage = data.get('profit_percentage')
        
        if result not in ['profit', 'loss']:
            return jsonify({'success': False, 'message': 'Invalid result.'})
        
        try:
            profit_percentage = float(profit_percentage)
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': 'Invalid profit percentage.'})
        
        signal.result = result
        signal.profit_percentage = profit_percentage
        signal.is_active = False
        db.session.commit()
        
        # Update all user positions for this signal
        positions = TradePosition.query.filter_by(signal_id=signal_id, status='open').all()
        
        for position in positions:
            # Calculate profit/loss
            position_profit = position.amount * (profit_percentage / 100)
            
            if result == 'loss':
                position_profit = -position_profit
            
            # Update position
            position.status = 'closed'
            position.profit_loss = position_profit
            position.profit_loss_percentage = profit_percentage if result == 'profit' else -profit_percentage
            position.closed_at = datetime.utcnow()
            
            # Update user's wallet
            wallet = Wallet.query.filter_by(user_id=position.user_id, currency=signal.currency_pair.split('/')[1]).first()
            
            if wallet:
                wallet.spot_balance += position.amount + position_profit
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Signal result updated to {result} with {profit_percentage}% {result}.',
            'result': signal.result,
            'profit_percentage': signal.profit_percentage
        })
    
    return jsonify({'success': False, 'message': 'Invalid action.'})

@admin.route('/announcements')
@login_required
@admin_required
def announcements():
    page = request.args.get('page', 1, type=int)
    
    # Get announcements
    announcements = Announcement.query.order_by(Announcement.created_at.desc()).paginate(page=page, per_page=20)
    
    return render_template('admin/announcements.html', 
                          title='Announcements Management',
                          announcements=announcements)

@admin.route('/create-announcement', methods=['GET', 'POST'])
@login_required
@admin_required
def create_announcement():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        priority = request.form.get('priority', 0)
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date', '')
        
        # Validate input
        if not title or not content:
            flash('Title and content are required.', 'danger')
            return redirect(url_for('admin.create_announcement'))
        
        try:
            priority = int(priority)
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            end_date = datetime.strptime(end_date, '%Y-%m-%d') if end_date else None
        except ValueError:
            flash('Invalid input. Please check your values.', 'danger')
            return redirect(url_for('admin.create_announcement'))
        
        # Create new announcement
        announcement = Announcement(
            title=title,
            content=content,
            priority=priority,
            start_date=start_date,
            end_date=end_date,
            created_by=current_user.id
        )
        
        db.session.add(announcement)
        db.session.commit()
        
        flash('Announcement created successfully!', 'success')
        return redirect(url_for('admin.announcements'))
    
    return render_template('admin/create_announcement.html', title='Create Announcement')

@admin.route('/update-announcement/<int:announcement_id>', methods=['POST'])
@login_required
@admin_required
def update_announcement(announcement_id):
    announcement = Announcement.query.get_or_404(announcement_id)
    
    # Check if the request is JSON or form data
    if request.is_json:
        data = request.json
    else:
        data = request.form
    
    action = data.get('action')
    
    if action == 'toggle_active':
        announcement.is_active = not announcement.is_active
        db.session.commit()
        return jsonify({
            'success': True,
            'message': f"Announcement {'activated' if announcement.is_active else 'deactivated'}.",
            'is_active': announcement.is_active
        })
    
    elif action == 'delete':
        db.session.delete(announcement)
        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Announcement deleted.'
        })
    
    return jsonify({'success': False, 'message': 'Invalid action.'})

@admin.route('/reports')
@login_required
@admin_required
def reports():
    report_type = request.args.get('type', 'users')
    period = request.args.get('period', 'week')
    
    # Generate report data based on type and period
    data = {}
    
    if report_type == 'users':
        if period == 'week':
            # Get user registrations for the last 7 days
            data['labels'] = [(datetime.utcnow() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7, 0, -1)]
            data['values'] = []
            
            for date in data['labels']:
                start_date = datetime.strptime(date, '%Y-%m-%d')
                end_date = start_date + timedelta(days=1)
                count = User.query.filter(User.created_at >= start_date, User.created_at < end_date).count()
                data['values'].append(count)
        
        elif period == 'month':
            # Get user registrations for the last 30 days
            data['labels'] = [(datetime.utcnow() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(30, 0, -1)]
            data['values'] = []
            
            for date in data['labels']:
                start_date = datetime.strptime(date, '%Y-%m-%d')
                end_date = start_date + timedelta(days=1)
                count = User.query.filter(User.created_at >= start_date, User.created_at < end_date).count()
                data['values'].append(count)
    
    elif report_type == 'transactions':
        if period == 'week':
            # Get transactions for the last 7 days
            data['labels'] = [(datetime.utcnow() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7, 0, -1)]
            data['deposits'] = []
            data['withdrawals'] = []
            
            for date in data['labels']:
                start_date = datetime.strptime(date, '%Y-%m-%d')
                end_date = start_date + timedelta(days=1)
                
                deposits = Transaction.query.filter(
                    Transaction.transaction_type == 'deposit',
                    Transaction.created_at >= start_date,
                    Transaction.created_at < end_date
                ).count()
                
                withdrawals = Transaction.query.filter(
                    Transaction.transaction_type == 'withdrawal',
                    Transaction.created_at >= start_date,
                    Transaction.created_at < end_date
                ).count()
                
                data['deposits'].append(deposits)
                data['withdrawals'].append(withdrawals)
        
        elif period == 'month':
            # Get transactions for the last 30 days
            data['labels'] = [(datetime.utcnow() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(30, 0, -1)]
            data['deposits'] = []
            data['withdrawals'] = []
            
            for date in data['labels']:
                start_date = datetime.strptime(date, '%Y-%m-%d')
                end_date = start_date + timedelta(days=1)
                
                deposits = Transaction.query.filter(
                    Transaction.transaction_type == 'deposit',
                    Transaction.created_at >= start_date,
                    Transaction.created_at < end_date
                ).count()
                
                withdrawals = Transaction.query.filter(
                    Transaction.transaction_type == 'withdrawal',
                    Transaction.created_at >= start_date,
                    Transaction.created_at < end_date
                ).count()
                
                data['deposits'].append(deposits)
                data['withdrawals'].append(withdrawals)
    
    return render_template('admin/reports.html', 
                          title='Reports',
                          report_type=report_type,
                          period=period,
                          data=data)