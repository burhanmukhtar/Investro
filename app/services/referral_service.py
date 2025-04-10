# app/services/referral_service.py
from app import db
from app.models.user import User, ReferralReward
from app.models.transaction import Transaction
from app.models.wallet import Wallet
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def get_reward_by_referred_user(referred_id):
    """
    Get referral reward for a specific referred user.
    
    Args:
        referred_id: ID of the referred user
    
    Returns:
        ReferralReward object or None
    """
    return ReferralReward.query.filter_by(referred_id=referred_id).first()

def is_eligible_for_referral_reward(user_id):
    """
    Check if a user is eligible for a referral reward.
    
    Args:
        user_id: ID of the user to check
    
    Returns:
        Boolean indicating if user is eligible
    """
    user = User.query.get(user_id)
    
    if not user:
        return False
    
    # Check if user was referred by someone
    if not user.referred_by:
        return False
    
    # Check if user has already generated a reward
    existing_reward = ReferralReward.query.filter_by(referred_id=user_id).first()
    if existing_reward:
        return False
    
    # Check if user has completed KYC verification
    if not user.is_verified:
        return False
    
    # Check if user has deposited at least 90 USDT
    if user.get_total_deposits() < 90:
        return False
    
    return True

def process_referral_reward(user_id):
    """
    Process referral reward for an eligible user.
    
    Args:
        user_id: ID of the user who triggered the reward
    
    Returns:
        Tuple of (success, message)
    """
    if not is_eligible_for_referral_reward(user_id):
        return False, "User is not eligible for a referral reward."
    
    try:
        user = User.query.get(user_id)
        
        # Find the referrer
        referrer = User.query.filter_by(referral_code=user.referred_by).first()
        
        if not referrer:
            return False, "Referrer not found."
        
        # Generate a unique transaction ID
        transaction_id = f"REF{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        # Create a transaction for the reward
        transaction = Transaction(
            user_id=referrer.id,
            transaction_type='referral',
            status='completed',
            currency='USDT',
            amount=80.0,  # Fixed 80 USDT reward
            fee=0,
            from_wallet='system',
            to_wallet='spot',
            notes=f"Referral reward for {user.username}",
            transaction_id=transaction_id
        )
        
        db.session.add(transaction)
        db.session.flush()  # Get transaction ID without committing
        
        # Create referral reward record
        reward = ReferralReward(
            referrer_id=referrer.id,
            referred_id=user_id,
            amount=80.0,
            currency='USDT',
            transaction_id=transaction.id,
            referred_username=user.username,
            status='completed'
        )
        
        db.session.add(reward)
        
        # Add the reward to referrer's wallet
        wallet = Wallet.query.filter_by(user_id=referrer.id, currency='USDT').first()
        
        if not wallet:
            wallet = Wallet(user_id=referrer.id, currency='USDT', spot_balance=0)
            db.session.add(wallet)
        
        wallet.spot_balance += 80.0
        
        db.session.commit()
        
        # Send email notification to referrer
        try:
            from app.services.email_notification_service import send_referral_notification
            send_referral_notification(referrer, reward)
            logger.info(f"Referral reward email notification sent to user {referrer.id}")
        except Exception as e:
            logger.error(f"Error sending referral reward email notification: {str(e)}")
        
        logger.info(f"Referral reward processed: {referrer.username} received 80 USDT for referring {user.username}")
        return True, "Referral reward processed successfully."
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error processing referral reward: {str(e)}")
        return False, f"Error processing referral reward: {str(e)}"