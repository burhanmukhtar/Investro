# app/services/admin_service.py
"""
Admin operations business logic.
Handles user management, verification processes, deposit/withdrawal approvals,
trade signals creation, and platform announcements.
"""
from datetime import datetime, timedelta
import logging
from app import db
from app.models.user import User, VerificationDocument
from app.models.wallet import Wallet
from app.models.transaction import Transaction
from app.models.trade_signal import TradeSignal, TradePosition
from app.models.announcement import Announcement
from app.services.notification_service import (
    send_verification_notification, send_transaction_notification,
    send_signal_notification
)

logger = logging.getLogger(__name__)

# User Management
def get_all_users(page=1, per_page=20, search=None):
    """
    Get paginated list of users with optional search.
    
    Args:
        page: Page number
        per_page: Number of items per page
        search: Optional search term
    
    Returns:
        Paginated users query
    """
    query = User.query
    
    if search:
        query = query.filter(
            (User.username.like(f'%{search}%')) |
            (User.email.like(f'%{search}%')) |
            (User.unique_id.like(f'%{search}%'))
        )
    
    return query.order_by(User.created_at.desc()).paginate(page=page, per_page=per_page)

def toggle_admin_status(user_id, admin_user_id):
    """
    Toggle admin status for a user.
    Only super admin (admin with ID 1) can perform this action.
    
    Args:
        user_id: ID of user to update
        admin_user_id: ID of admin making the request
    
    Returns:
        Tuple of (success, message, is_admin)
    """
    try:
        # Check if admin is super admin
        if admin_user_id != 1:
            return False, "Only super admin can perform this action.", None
        
        user = User.query.get(user_id)
        if not user:
            return False, "User not found.", None
        
        # Toggle admin status
        user.is_admin = not user.is_admin
        db.session.commit()
        
        return True, f"Admin status {'enabled' if user.is_admin else 'disabled'} for {user.username}.", user.is_admin
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error toggling admin status: {str(e)}")
        return False, f"Error toggling admin status: {str(e)}", None

# Verification Management
def get_verifications_by_status(status, page=1, per_page=20):
    """
    Get paginated list of verification documents by status.
    
    Args:
        status: Document status ('pending', 'approved', 'rejected')
        page: Page number
        per_page: Number of items per page
    
    Returns:
        Paginated verification documents query
    """
    query = VerificationDocument.query.filter_by(status=status)
    return query.order_by(VerificationDocument.submitted_at.desc()).paginate(page=page, per_page=per_page)

def process_verification(document_id, action, admin_notes=None):
    """
    Process a verification document request.
    
    Args:
        document_id: Verification document ID
        action: Action to take ('approve' or 'reject')
        admin_notes: Optional notes from admin
    
    Returns:
        Tuple of (success, message)
    """
    try:
        document = VerificationDocument.query.get(document_id)
        if not document:
            return False, "Document not found."
        
        if document.status != 'pending':
            return False, "Document is not pending verification."
        
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
        
        # Send original notification to user
        send_verification_notification(user, document.status, admin_notes)
        
        # Send new email notification
        try:
            from app.services.email_notification_service import send_verification_status_notification
            send_verification_status_notification(user, document.status, admin_notes)
            logger.info(f"Verification {document.status} email notification sent to user {user.id}")
        except Exception as e:
            logger.error(f"Error sending verification email notification: {str(e)}")
        
        return True, f"Verification document {document.status}."
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error processing verification: {str(e)}")
        return False, f"Error processing verification: {str(e)}"

# Transaction Management
def get_deposits_by_status(status, page=1, per_page=20):
    """
    Get paginated list of deposit transactions by status.
    
    Args:
        status: Transaction status ('pending', 'completed', 'failed')
        page: Page number
        per_page: Number of items per page
    
    Returns:
        Paginated deposit transactions query
    """
    query = Transaction.query.filter_by(transaction_type='deposit', status=status)
    return query.order_by(Transaction.created_at.desc()).paginate(page=page, per_page=per_page)

def get_withdrawals_by_status(status, page=1, per_page=20):
    """
    Get paginated list of withdrawal transactions by status.
    
    Args:
        status: Transaction status ('pending', 'completed', 'failed')
        page: Page number
        per_page: Number of items per page
    
    Returns:
        Paginated withdrawal transactions query
    """
    query = Transaction.query.filter_by(transaction_type='withdrawal', status=status)
    return query.order_by(Transaction.created_at.desc()).paginate(page=page, per_page=per_page)

# Updated process_deposit function in app/services/admin_service.py

def process_deposit(transaction_id, action, admin_notes=None):
    """
    Process a deposit transaction.
    
    Args:
        transaction_id: Transaction ID
        action: Action to take ('approve' or 'reject')
        admin_notes: Optional notes from admin
    
    Returns:
        Tuple of (success, message)
    """
    try:
        transaction = Transaction.query.get(transaction_id)
        if not transaction:
            return False, "Transaction not found."
        
        if transaction.transaction_type != 'deposit':
            return False, "Transaction is not a deposit."
        
        if transaction.status != 'pending':
            return False, "Transaction is not pending."
        
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
            
            # Log the wallet update
            logger.info(f"Updated user {transaction.user_id} wallet balance: +{transaction.amount} {transaction.currency}")
        
        db.session.commit()
        
        # Send notification to user using both methods
        user = User.query.get(transaction.user_id)
        
        # Original notification method
        send_transaction_notification(user, transaction)
        
        # New email notification
        try:
            from app.services.email_notification_service import send_transaction_notification as send_email_transaction_notification
            send_email_transaction_notification(user, transaction)
            logger.info(f"Deposit {transaction.status} email notification sent to user {user.id}")
        except Exception as e:
            logger.error(f"Error sending deposit email notification: {str(e)}")
        
        return True, f"Deposit {transaction.status}."
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error processing deposit: {str(e)}")
        return False, f"Error processing deposit: {str(e)}"

def process_withdrawal(transaction_id, action, blockchain_txid=None, admin_notes=None):
    """
    Process a withdrawal transaction.
    
    Args:
        transaction_id: Transaction ID
        action: Action to take ('approve' or 'reject')
        blockchain_txid: Blockchain transaction ID (if approved)
        admin_notes: Optional notes from admin
    
    Returns:
        Tuple of (success, message)
    """
    try:
        transaction = Transaction.query.get(transaction_id)
        if not transaction:
            return False, "Transaction not found."
        
        if transaction.transaction_type != 'withdrawal':
            return False, "Transaction is not a withdrawal."
        
        if transaction.status != 'pending':
            return False, "Transaction is not pending."
        
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
        
        # Send notification to user using both methods
        user = User.query.get(transaction.user_id)
        
        # Original notification method
        send_transaction_notification(user, transaction)
        
        # New email notification
        try:
            from app.services.email_notification_service import send_transaction_notification as send_email_transaction_notification
            send_email_transaction_notification(user, transaction)
            logger.info(f"Withdrawal {transaction.status} email notification sent to user {user.id}")
        except Exception as e:
            logger.error(f"Error sending withdrawal email notification: {str(e)}")
        
        return True, f"Withdrawal {transaction.status}."
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error processing withdrawal: {str(e)}")
        return False, f"Error processing withdrawal: {str(e)}"

# Trade Signals Management
def get_trade_signals(status='active', page=1, per_page=20):
    """
    Get paginated list of trade signals by status.
    
    Args:
        status: Signal status ('active', 'expired', or 'all')
        page: Page number
        per_page: Number of items per page
    
    Returns:
        Paginated trade signals query
    """
    query = TradeSignal.query
    
    if status == 'active':
        query = query.filter_by(is_active=True)
    elif status == 'expired':
        query = query.filter_by(is_active=False)
    
    return query.order_by(TradeSignal.created_at.desc()).paginate(page=page, per_page=per_page)

def create_trade_signal(admin_id, data):
    """
    Create a new trade signal.
    
    Args:
        admin_id: Admin user ID
        data: Dictionary containing signal data
    
    Returns:
        Tuple of (success, message, signal)
    """
    try:
        # Create new trade signal
        signal = TradeSignal(
            admin_id=admin_id,
            currency_pair=data['currency_pair'],
            signal_type=data['signal_type'],
            entry_price=float(data['entry_price']),
            target_price=float(data['target_price']),
            stop_loss=float(data['stop_loss']),
            leverage=int(data['leverage']),
            description=data.get('description', ''),
            expiry_time=datetime.utcnow() + timedelta(hours=int(data['expiry_hours']))
        )
        
        db.session.add(signal)
        db.session.commit()
        
        # Send notification to all verified users
        # In a real implementation, you would filter users who are subscribed to signals
        try:
            # Import the notification service
            from app.services.email_notification_service import send_trade_signal_notification
            
            # Get verified users
            users = User.query.filter_by(is_verified=True).all()
            
            # Send notification to each user
            for user in users:
                send_trade_signal_notification(user, signal)
                
            # Also send the original notification via older method (for backward compatibility)
            send_signal_notification(users, signal)
            
            logger.info(f"Trade signal notifications sent to {len(users)} users")
        except Exception as e:
            logger.error(f"Error sending trade signal notifications: {str(e)}")
        
        return True, "Trade signal created successfully.", signal
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating trade signal: {str(e)}")
        return False, f"Error creating trade signal: {str(e)}", None

def deactivate_signal(signal_id):
    """
    Deactivate a trade signal.
    
    Args:
        signal_id: Signal ID
    
    Returns:
        Tuple of (success, message)
    """
    try:
        signal = TradeSignal.query.get(signal_id)
        if not signal:
            return False, "Signal not found."
        
        signal.is_active = False
        db.session.commit()
        
        return True, "Signal deactivated."
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deactivating signal: {str(e)}")
        return False, f"Error deactivating signal: {str(e)}"

def update_signal_result(signal_id, result, profit_percentage):
    """
    Update the result of a trade signal and close all related positions.
    Returns funds to futures wallets.
    
    Args:
        signal_id: Signal ID
        result: Result ('profit' or 'loss')
        profit_percentage: Profit/loss percentage
    
    Returns:
        Tuple of (success, message)
    """
    try:
        signal = TradeSignal.query.get(signal_id)
        if not signal:
            return False, "Signal not found."
        
        signal.result = result
        signal.profit_percentage = float(profit_percentage)
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
            
            # Update user's FUTURES wallet (not spot wallet)
            wallet = Wallet.query.filter_by(user_id=position.user_id, currency=signal.currency_pair.split('/')[1]).first()
            
            if wallet:
                # Ensure futures_balance exists and is a float
                if not hasattr(wallet, 'futures_balance') or wallet.futures_balance is None:
                    wallet.futures_balance = 0.0
                    
                # Return original amount plus profit (or minus loss) to futures wallet
                wallet.futures_balance += position.amount + position_profit
        
        db.session.commit()
        
        return True, f"Signal result updated to {result} with {profit_percentage}% {result}."
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating signal result: {str(e)}")
        return False, f"Error updating signal result: {str(e)}"

# Announcements Management
# app/services/admin_service.py (continued)
def get_announcements(page=1, per_page=20):
    """
    Get paginated list of announcements.
    
    Args:
        page: Page number
        per_page: Number of items per page
    
    Returns:
        Paginated announcements query
    """
    query = Announcement.query
    return query.order_by(Announcement.created_at.desc()).paginate(page=page, per_page=per_page)

def create_announcement(admin_id, data):
    """
    Create a new announcement.
    
    Args:
        admin_id: Admin user ID
        data: Dictionary containing announcement data
    
    Returns:
        Tuple of (success, message, announcement)
    """
    try:
        # Create new announcement
        announcement = Announcement(
            title=data['title'],
            content=data['content'],
            priority=int(data.get('priority', 0)),
            start_date=datetime.strptime(data['start_date'], '%Y-%m-%d'),
            end_date=datetime.strptime(data['end_date'], '%Y-%m-%d') if data.get('end_date') else None,
            created_by=admin_id
        )
        
        db.session.add(announcement)
        db.session.commit()
        
        return True, "Announcement created successfully.", announcement
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating announcement: {str(e)}")
        return False, f"Error creating announcement: {str(e)}", None

def toggle_announcement_status(announcement_id):
    """
    Toggle the active status of an announcement.
    
    Args:
        announcement_id: Announcement ID
    
    Returns:
        Tuple of (success, message, is_active)
    """
    try:
        announcement = Announcement.query.get(announcement_id)
        if not announcement:
            return False, "Announcement not found.", None
        
        announcement.is_active = not announcement.is_active
        db.session.commit()
        
        return True, f"Announcement {'activated' if announcement.is_active else 'deactivated'}.", announcement.is_active
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error toggling announcement status: {str(e)}")
        return False, f"Error toggling announcement status: {str(e)}", None

def delete_announcement(announcement_id):
    """
    Delete an announcement.
    
    Args:
        announcement_id: Announcement ID
    
    Returns:
        Tuple of (success, message)
    """
    try:
        announcement = Announcement.query.get(announcement_id)
        if not announcement:
            return False, "Announcement not found."
        
        db.session.delete(announcement)
        db.session.commit()
        
        return True, "Announcement deleted."
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting announcement: {str(e)}")
        return False, f"Error deleting announcement: {str(e)}"

# Reports and Statistics
def get_user_registrations_stats(period='week'):
    """
    Get user registration statistics for the specified period.
    
    Args:
        period: Time period ('week' or 'month')
    
    Returns:
        Dictionary with labels and values for chart
    """
    days = 7 if period == 'week' else 30
    
    data = {
        'labels': [],
        'values': []
    }
    
    for i in range(days, 0, -1):
        date = (datetime.utcnow() - timedelta(days=i)).strftime('%Y-%m-%d')
        start_date = datetime.strptime(date, '%Y-%m-%d')
        end_date = start_date + timedelta(days=1)
        
        count = User.query.filter(
            User.created_at >= start_date,
            User.created_at < end_date
        ).count()
        
        data['labels'].append(date)
        data['values'].append(count)
    
    return data

def get_transaction_stats(period='week'):
    """
    Get transaction statistics for the specified period.
    
    Args:
        period: Time period ('week' or 'month')
    
    Returns:
        Dictionary with labels and values for chart
    """
    days = 7 if period == 'week' else 30
    
    data = {
        'labels': [],
        'deposits': [],
        'withdrawals': []
    }
    
    for i in range(days, 0, -1):
        date = (datetime.utcnow() - timedelta(days=i)).strftime('%Y-%m-%d')
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
        
        data['labels'].append(date)
        data['deposits'].append(deposits)
        data['withdrawals'].append(withdrawals)
    
    return data

def get_dashboard_stats():
    """
    Get statistics for the admin dashboard.
    
    Returns:
        Dictionary with various statistics
    """
    stats = {
        'total_users': User.query.count(),
        'verified_users': User.query.filter_by(is_verified=True).count(),
        'pending_verifications': VerificationDocument.query.filter_by(status='pending').count(),
        'pending_deposits': Transaction.query.filter_by(transaction_type='deposit', status='pending').count(),
        'pending_withdrawals': Transaction.query.filter_by(transaction_type='withdrawal', status='pending').count(),
        'active_signals': TradeSignal.query.filter_by(is_active=True).count(),
        'recent_users': User.query.order_by(User.created_at.desc()).limit(10).all(),
        'recent_transactions': Transaction.query.order_by(Transaction.created_at.desc()).limit(10).all()
    }
    
    return stats

def get_user_details(user_id):
    """
    Get detailed information about a user for admin view.
    
    Args:
        user_id: User ID
    
    Returns:
        Dictionary with user details
    """
    user = User.query.get(user_id)
    
    if not user:
        return None
    
    details = {
        'user': user,
        'wallets': Wallet.query.filter_by(user_id=user_id).all(),
        'transactions': Transaction.query.filter_by(user_id=user_id).order_by(Transaction.created_at.desc()).limit(20).all(),
        'verification_documents': VerificationDocument.query.filter_by(user_id=user_id).all(),
        'referred_users': User.query.filter_by(referred_by=user.referral_code).all(),
        'positions': TradePosition.query.filter_by(user_id=user_id).order_by(TradePosition.created_at.desc()).limit(10).all()
    }
    
    return details