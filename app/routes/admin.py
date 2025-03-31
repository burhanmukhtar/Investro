# app/routes/admin.py
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, current_app
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
import logging
from app.config import Config
from app.models.support_ticket import SupportTicket, TicketResponse

# Add this line after the existing imports
logger = logging.getLogger(__name__)

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

# In app/routes/admin.py

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
    
    # Get support ticket stats
    from app.models.support_ticket import SupportTicket
    open_tickets = SupportTicket.query.filter_by(status='open').count()
    
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
                          open_tickets=open_tickets,  # Add this line
                          recent_users=recent_users,
                          recent_transactions=recent_transactions,
                          stats={'open_tickets': open_tickets})  # Add this line

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
    """
    Process verification document approval or rejection
    """
    try:
        document = VerificationDocument.query.get_or_404(doc_id)
        
        # Get form data
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form
        
        action = data.get('action')
        admin_notes = data.get('admin_notes', '')
        
        if action not in ['approve', 'reject']:
            return jsonify({'success': False, 'message': 'Invalid action.'}), 400
        
        # Update document status
        document.status = 'approved' if action == 'approve' else 'rejected'
        document.admin_notes = admin_notes
        document.reviewed_at = datetime.utcnow()
        
        # Update user's verification status if approved
        user = User.query.get(document.user_id)
        if not user:
            return jsonify({'success': False, 'message': 'User not found.'}), 404
            
        if action == 'approve':
            user.verification_status = 'approved'
            user.is_verified = True
            user.email_verified = True  # Ensure email verification is set
        else:
            user.verification_status = 'rejected'
        
        db.session.commit()
        
        # Send notification to user
        try:
            from app.services.notification_service import send_verification_notification
            send_verification_notification(user, document.status, admin_notes)
        except Exception as e:
            # Log the error but don't fail the request
            current_app.logger.error(f"Error sending notification: {str(e)}")
        
        return jsonify({
            'success': True,
            'message': f"Document {document.status} successfully.",
            'status': document.status
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error processing verification: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error processing verification: {str(e)}"
        }), 500

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
        announcement_type = request.form.get('type')
        priority = request.form.get('priority', 'normal')
        action_text = request.form.get('action_text')
        action_url = request.form.get('action_url')
        has_countdown = 'has_countdown' in request.form
        expiry_date = None
        
        if request.form.get('expiry_date'):
            try:
                expiry_date = datetime.strptime(request.form.get('expiry_date'), '%Y-%m-%d')
            except ValueError:
                flash('Invalid date format for expiry date.', 'danger')
                return redirect(url_for('admin.create_announcement'))
        
        # Create new announcement
        announcement = Announcement(
            title=title,
            content=content,
            type=announcement_type,
            priority=priority,
            action_text=action_text,
            action_url=action_url,
            has_countdown=has_countdown,
            expiry_date=expiry_date,
            created_by=current_user.id
        )
        
        db.session.add(announcement)
        db.session.commit()
        
        flash('Announcement created successfully!', 'success')
        return redirect(url_for('admin.announcements'))
    
    return render_template('admin/create_announcement.html', title='Create Announcement')
@admin.route('/edit-announcement/<int:announcement_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_announcement(announcement_id):
    announcement = Announcement.query.get_or_404(announcement_id)
    
    if request.method == 'POST':
        announcement.title = request.form.get('title')
        announcement.content = request.form.get('content')
        announcement.type = request.form.get('type')
        announcement.priority = request.form.get('priority', 'normal')
        announcement.action_text = request.form.get('action_text')
        announcement.action_url = request.form.get('action_url')
        announcement.has_countdown = 'has_countdown' in request.form
        
        if request.form.get('expiry_date'):
            try:
                announcement.expiry_date = datetime.strptime(request.form.get('expiry_date'), '%Y-%m-%d')
            except ValueError:
                flash('Invalid date format for expiry date.', 'danger')
                return redirect(url_for('admin.edit_announcement', announcement_id=announcement_id))
        else:
            announcement.expiry_date = None
        
        db.session.commit()
        
        flash('Announcement updated successfully!', 'success')
        return redirect(url_for('admin.announcements'))
    
    return render_template('admin/edit_announcement.html', 
                          title='Edit Announcement',
                          announcement=announcement)

@admin.route('/toggle-announcement/<int:announcement_id>', methods=['POST'])
@login_required
@admin_required
def toggle_announcement(announcement_id):
    announcement = Announcement.query.get_or_404(announcement_id)
    
    announcement.is_active = not announcement.is_active
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f"Announcement {'activated' if announcement.is_active else 'deactivated'}.",
        'is_active': announcement.is_active
    })

@admin.route('/delete-announcement/<int:announcement_id>', methods=['POST'])
@login_required
@admin_required
def delete_announcement(announcement_id):
    announcement = Announcement.query.get_or_404(announcement_id)
    
    db.session.delete(announcement)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Announcement deleted successfully.'
    })

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


# Add these routes to app/routes/admin.py

@admin.route('/support')
@login_required
@admin_required
def support():
    """
    Support ticket management for admin
    """
    try:
        # Get query parameters
        status = request.args.get('status')
        priority = request.args.get('priority')
        search = request.args.get('search')
        page = request.args.get('page', 1, type=int)
        
        # Get ticket statistics
        from app.services.support_service import get_ticket_statistics
        stats = get_ticket_statistics()
        
        # Get tickets with filtering
        from app.services.support_service import get_all_tickets
        tickets = get_all_tickets(
            status=status,
            priority=priority,
            page=page,
            per_page=20
        )
        
        # Search functionality (simple implementation)
        # For a more comprehensive search, you might want to use a proper search engine
        if search:
            from app.models.support_ticket import SupportTicket
            from sqlalchemy import or_
            
            query = SupportTicket.query
            
            # Filter by status if specified
            if status:
                query = query.filter_by(status=status)
                
            # Filter by priority if specified
            if priority:
                query = query.filter_by(priority=priority)
                
            # Search in ticket number, subject, and message
            query = query.filter(
                or_(
                    SupportTicket.ticket_number.ilike(f'%{search}%'),
                    SupportTicket.subject.ilike(f'%{search}%'),
                    SupportTicket.message.ilike(f'%{search}%')
                )
            )
            
            # Order by priority and created date
            query = query.order_by(SupportTicket.created_at.desc())
            
            # Paginate results
            tickets = query.paginate(page=page, per_page=20)
        
        return render_template('admin/support.html',
                              title='Support Management',
                              tickets=tickets,
                              stats=stats,
                              status=status,
                              priority=priority,
                              search=search)
    except Exception as e:
        logger.error(f"Error loading admin support page: {str(e)}")
        flash(f"Error loading support management: {str(e)}", "danger")
        return redirect(url_for('admin.dashboard'))

@admin.route('/support/ticket/<int:ticket_id>')
@login_required
@admin_required
def ticket_detail(ticket_id):
    """
    View a specific support ticket (admin view)
    """
    try:
        # Get ticket details
        from app.services.support_service import get_ticket_details
        ticket_details = get_ticket_details(ticket_id)
        
        if not ticket_details:
            flash("Ticket not found.", "danger")
            return redirect(url_for('admin.support'))
        
        return render_template('admin/ticket_detail.html',
                              title=f'Ticket #{ticket_details["ticket"].ticket_number}',
                              ticket=ticket_details['ticket'],
                              user=ticket_details['user'],
                              responses=ticket_details['responses'])
    except Exception as e:
        logger.error(f"Error viewing ticket details: {str(e)}")
        flash(f"Error viewing ticket details: {str(e)}", "danger")
        return redirect(url_for('admin.support'))

@admin.route('/support/ticket/<int:ticket_id>/reply', methods=['POST'])
@login_required
@admin_required
def reply_ticket(ticket_id):
    """
    Reply to a support ticket as admin
    """
    try:
        message = request.form.get('message')
        attachment = request.files.get('attachment')
        close_ticket = 'close_ticket' in request.form
        
        if not message:
            flash("Please enter a message.", "danger")
            return redirect(url_for('admin.ticket_detail', ticket_id=ticket_id))
        
        # Add admin response to ticket
        from app.services.support_service import add_ticket_response, update_ticket_status
        success, message_text, response = add_ticket_response(
            ticket_id=ticket_id,
            message=message,
            admin_id=current_user.id,
            attachment=attachment
        )
        
        if not success:
            flash(message_text, "danger")
            return redirect(url_for('admin.ticket_detail', ticket_id=ticket_id))
        
        # Close ticket if requested
        if close_ticket:
            update_success, update_message = update_ticket_status(
                ticket_id=ticket_id,
                status='closed',
                admin_id=current_user.id
            )
            
            if update_success:
                flash("Your response has been sent and the ticket has been closed.", "success")
            else:
                flash(f"Response sent but could not close ticket: {update_message}", "warning")
        else:
            flash("Your response has been sent.", "success")
        
        return redirect(url_for('admin.ticket_detail', ticket_id=ticket_id))
    except Exception as e:
        logger.error(f"Error replying to ticket: {str(e)}")
        flash(f"Error replying to ticket: {str(e)}", "danger")
        return redirect(url_for('admin.ticket_detail', ticket_id=ticket_id))

@admin.route('/support/ticket/<int:ticket_id>/status', methods=['POST'])
@login_required
@admin_required
def update_ticket_status(ticket_id):
    """
    Update a ticket's status
    """
    try:
        status = request.form.get('status')
        
        if not status or status not in ['open', 'in_progress', 'closed']:
            flash("Invalid status.", "danger")
            return redirect(url_for('admin.ticket_detail', ticket_id=ticket_id))
        
        # Update ticket status
        from app.services.support_service import update_ticket_status
        success, message_text = update_ticket_status(
            ticket_id=ticket_id,
            status=status,
            admin_id=current_user.id
        )
        
        if success:
            flash(f"Ticket status updated to '{status}'.", "success")
        else:
            flash(message_text, "danger")
        
        return redirect(url_for('admin.ticket_detail', ticket_id=ticket_id))
    except Exception as e:
        logger.error(f"Error updating ticket status: {str(e)}")
        flash(f"Error updating ticket status: {str(e)}", "danger")
        return redirect(url_for('admin.ticket_detail', ticket_id=ticket_id))

@admin.route('/support/ticket/<int:ticket_id>/priority', methods=['POST'])
@login_required
@admin_required
def update_ticket_priority(ticket_id):
    """
    Update a ticket's priority
    """
    try:
        priority = request.form.get('priority')
        
        if not priority or priority not in ['low', 'normal', 'high', 'urgent']:
            flash("Invalid priority.", "danger")
            return redirect(url_for('admin.ticket_detail', ticket_id=ticket_id))
        
        # Update ticket priority
        from app.services.support_service import update_ticket_priority
        success, message_text = update_ticket_priority(
            ticket_id=ticket_id,
            priority=priority,
            admin_id=current_user.id
        )
        
        if success:
            flash(f"Ticket priority updated to '{priority}'.", "success")
        else:
            flash(message_text, "danger")
        
        return redirect(url_for('admin.ticket_detail', ticket_id=ticket_id))
    except Exception as e:
        logger.error(f"Error updating ticket priority: {str(e)}")
        flash(f"Error updating ticket priority: {str(e)}", "danger")
        return redirect(url_for('admin.ticket_detail', ticket_id=ticket_id))

@admin.route('/support/ticket/<int:ticket_id>/print')
@login_required
@admin_required
def print_ticket(ticket_id):
    """
    Print-friendly view of a ticket
    """
    try:
        # Get ticket details
        from app.services.support_service import get_ticket_details
        ticket_details = get_ticket_details(ticket_id)
        
        if not ticket_details:
            flash("Ticket not found.", "danger")
            return redirect(url_for('admin.support'))
        
        return render_template('admin/print_ticket.html',
                              title=f'Print Ticket #{ticket_details["ticket"].ticket_number}',
                              ticket=ticket_details['ticket'],
                              user=ticket_details['user'],
                              responses=ticket_details['responses'],
                              hide_header=True,
                              hide_bottom_nav=True)
    except Exception as e:
        logger.error(f"Error printing ticket: {str(e)}")
        flash(f"Error printing ticket: {str(e)}", "danger")
        return redirect(url_for('admin.ticket_detail', ticket_id=ticket_id))

@admin.route('/download/attachment/<filename>')
@login_required
@admin_required
def download_attachment(filename):
    """
    Download support ticket attachment (admin access)
    """
    try:
        from flask import send_from_directory
        import os
        
        upload_dir = os.path.join(Config.UPLOAD_FOLDER, 'support_attachments')
        return send_from_directory(upload_dir, filename)
    except Exception as e:
        logger.error(f"Error downloading attachment: {str(e)}")
        flash(f"Error downloading attachment: {str(e)}", "danger")
        return redirect(url_for('admin.support'))
    

@admin.route('/wallet-addresses')
@login_required
@admin_required
def wallet_addresses():
    """
    Admin page for managing deposit wallet addresses
    """
    try:
        # Get all deposit addresses
        from app.models.deposit_address import DepositAddress
        
        # Get BTC addresses
        btc_addresses = {
            'BTC': DepositAddress.query.filter_by(currency='BTC', network='BTC').first(),
            'BSC': DepositAddress.query.filter_by(currency='BTC', network='BSC').first()
        }
        
        # Get USDT addresses
        usdt_addresses = {
            'TRC20': DepositAddress.query.filter_by(currency='USDT', network='TRC20').first(),
            'ERC20': DepositAddress.query.filter_by(currency='USDT', network='ERC20').first()
        }
        
        return render_template('admin/wallet_addresses.html',
                              title='Wallet Address Management',
                              btc_addresses=btc_addresses,
                              usdt_addresses=usdt_addresses)
    except Exception as e:
        logger.error(f"Error loading wallet addresses page: {str(e)}")
        flash(f"Error loading wallet addresses: {str(e)}", "danger")
        return redirect(url_for('admin.dashboard'))

# Update the update_wallet_address function in app/routes/admin.py

@admin.route('/wallet-addresses/update', methods=['POST'])
@login_required
@admin_required
def update_wallet_address():
    """
    Update or create a wallet address for deposits with QR code upload support
    """
    try:
        # Get form data
        currency = request.form.get('currency')
        network = request.form.get('network')
        address = request.form.get('address')
        qr_file = request.files.get('qr_code')
        
        if not currency or not network or not address:
            flash("Currency, network, and address are required.", "danger")
            return redirect(url_for('admin.wallet_addresses'))
        
        # Validate the address format based on network
        from app.utils.validators import validate_blockchain_address
        if not validate_blockchain_address(address, currency, network):
            flash(f"The address format is not valid for {currency} on {network}.", "danger")
            return redirect(url_for('admin.wallet_addresses'))
        
        # Find existing address or create new one
        from app.models.deposit_address import DepositAddress
        
        deposit_address = DepositAddress.query.filter_by(
            currency=currency,
            network=network
        ).first()
        
        qr_code_path = None
        # Process QR code if provided
        if qr_file and qr_file.filename:
            # Validate file type
            allowed_extensions = {'png', 'jpg', 'jpeg', 'svg'}
            if '.' in qr_file.filename and qr_file.filename.rsplit('.', 1)[1].lower() in allowed_extensions:
                # Generate secure filename
                from werkzeug.utils import secure_filename
                filename = secure_filename(f"{currency}_{network}_qr_{int(datetime.utcnow().timestamp())}.{qr_file.filename.rsplit('.', 1)[1].lower()}")
                
                # Ensure directory exists
                import os
                from app.config import Config
                upload_dir = os.path.join(Config.UPLOAD_FOLDER, 'qr_codes')
                os.makedirs(upload_dir, exist_ok=True)
                
                # Save file
                filepath = os.path.join(upload_dir, filename)
                qr_file.save(filepath)
                
                qr_code_path = filename
            else:
                flash(f"Invalid QR code file format. Allowed formats: PNG, JPG, JPEG, SVG", "danger")
        
        if deposit_address:
            # Update existing address
            deposit_address.address = address
            deposit_address.created_by = current_user.id
            deposit_address.updated_at = datetime.utcnow()
            # Only update QR code path if a new one was uploaded
            if qr_code_path:
                deposit_address.qr_code_path = qr_code_path
        else:
            # Create new address
            deposit_address = DepositAddress(
                currency=currency,
                network=network,
                address=address,
                qr_code_path=qr_code_path,
                created_by=current_user.id
            )
            db.session.add(deposit_address)
        
        db.session.commit()
        
        flash(f"Deposit address for {currency} on {network} updated successfully.", "success")
        return redirect(url_for('admin.wallet_addresses'))
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating wallet address: {str(e)}")
        flash(f"Error updating wallet address: {str(e)}", "danger")
        return redirect(url_for('admin.wallet_addresses'))