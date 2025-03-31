# app/services/wallet_service.py
import random
import string
import re
import logging
from datetime import datetime
from app import db
from app.models.wallet import Wallet
from app.models.transaction import Transaction
from app.models.user import User
from app.utils.crypto_api import get_current_price, get_coin_details

logger = logging.getLogger(__name__)

def generate_blockchain_address(user_id, currency, chain):
    """
    Generate a blockchain address for deposits.
    
    This is a placeholder function. In a real implementation, you would integrate
    with a cryptocurrency wallet or node to generate actual blockchain addresses.
    
    For development, this returns a mock address.
    """
    # For development, generate a realistic-looking mock address
    if chain == 'TRC20':
        # TRC20 addresses start with T and are 34 characters long
        address = 'T' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=33))
    elif chain == 'ERC20':
        # ERC20 addresses start with 0x and are 42 characters long
        address = '0x' + ''.join(random.choices('0123456789abcdef', k=40))
    else:
        # Generic address
        address = ''.join(random.choices(string.ascii_uppercase + string.digits, k=34))
    
    return address

def validate_address(address, currency, chain):
    """
    Validate a blockchain address.
    
    This is a placeholder function. In a real implementation, you would integrate
    with a cryptocurrency wallet or node to validate addresses.
    
    For development, this does a basic format check.
    """
    if chain == 'TRC20':
        # TRC20 addresses start with T and are 34 characters long
        return bool(re.match(r'^T[A-Za-z0-9]{33}$', address))
    elif chain == 'ERC20':
        # ERC20 addresses start with 0x and are 42 characters long
        return bool(re.match(r'^0x[0-9a-fA-F]{40}$', address))
    else:
        # Generic address
        return len(address) >= 30

def get_wallet_balance(user_id, currency, wallet_type='spot'):
    """
    Get the wallet balance for a user and currency.
    
    Args:
        user_id: User ID
        currency: Currency code
        wallet_type: Type of wallet ('spot', 'funding', or 'futures')
    
    Returns:
        Float balance amount
    """
    wallet = Wallet.query.filter_by(user_id=user_id, currency=currency).first()
    
    if not wallet:
        return 0.0
    
    if wallet_type == 'spot':
        return float(wallet.spot_balance) if wallet.spot_balance is not None else 0.0
    elif wallet_type == 'funding':
        return float(wallet.funding_balance) if wallet.funding_balance is not None else 0.0
    elif wallet_type == 'futures':
        return float(wallet.futures_balance) if wallet.futures_balance is not None else 0.0
    else:
        return 0.0

def create_wallet(user_id, currency):
    """
    Create a new wallet for a user and currency.
    
    Returns the created wallet.
    """
    wallet = Wallet(
        user_id=user_id,
        currency=currency,
        spot_balance=0.0,
        funding_balance=0.0,
        futures_balance=0.0
    )
    
    db.session.add(wallet)
    db.session.commit()
    
    return wallet

def add_balance(user_id, currency, amount, wallet_type='spot'):
    """
    Add balance to a user's wallet.
    
    Returns the updated wallet.
    """
    wallet = Wallet.query.filter_by(user_id=user_id, currency=currency).first()
    
    if not wallet:
        wallet = create_wallet(user_id, currency)
    
    # Ensure we're working with float values
    amount = float(amount)
    
    if wallet_type == 'spot':
        wallet.spot_balance = float(wallet.spot_balance or 0.0) + amount
    elif wallet_type == 'funding':
        wallet.funding_balance = float(wallet.funding_balance or 0.0) + amount
    else:  # wallet_type == 'futures'
        wallet.futures_balance = float(wallet.futures_balance or 0.0) + amount
    
    db.session.commit()
    
    return wallet

def subtract_balance(user_id, currency, amount, wallet_type='spot'):
    """
    Subtract balance from a user's wallet.
    
    Returns a tuple of (success, message, wallet).
    """
    wallet = Wallet.query.filter_by(user_id=user_id, currency=currency).first()
    
    if not wallet:
        return False, "Wallet not found.", None
    
    # Ensure we're working with float values
    amount = float(amount)
    
    if wallet_type == 'spot':
        current_balance = float(wallet.spot_balance or 0.0)
        if current_balance < amount:
            return False, "Insufficient balance.", wallet
        wallet.spot_balance = current_balance - amount
    elif wallet_type == 'funding':
        current_balance = float(wallet.funding_balance or 0.0)
        if current_balance < amount:
            return False, "Insufficient balance.", wallet
        wallet.funding_balance = current_balance - amount
    else:  # wallet_type == 'futures'
        current_balance = float(wallet.futures_balance or 0.0)
        if current_balance < amount:
            return False, "Insufficient balance.", wallet
        wallet.futures_balance = current_balance - amount
    
    db.session.commit()
    
    return True, "Balance subtracted successfully.", wallet

def transfer_balance(from_user_id, to_user_id, currency, amount, from_wallet_type='spot', to_wallet_type='spot'):
    """
    Transfer balance between users.
    
    Returns a tuple of (success, message).
    """
    # Subtract from sender
    success, message, sender_wallet = subtract_balance(from_user_id, currency, amount, from_wallet_type)
    
    if not success:
        return False, message
    
    # Add to recipient
    recipient_wallet = add_balance(to_user_id, currency, amount, to_wallet_type)
    
    return True, "Transfer completed successfully."

def get_conversion_rate(from_currency, to_currency):
    """
    Get the conversion rate between two currencies using CoinGecko API.
    
    Args:
        from_currency: Source currency code
        to_currency: Target currency code
    
    Returns:
        float: Exchange rate or 0 if error
    """
    try:
        # For same currency, rate is 1:1
        if from_currency == to_currency:
            return 1.0
            
        # For USDT to other currencies
        if from_currency == 'USDT':
            # Get the price in USDT terms (which is approximately USD)
            rate = get_current_price(f"{to_currency}/USDT")
            if rate and rate > 0:
                return 1.0 / rate  # Inverse since we want USDT to other currency
            return 0.0
            
        # For other currencies to USDT
        elif to_currency == 'USDT':
            # Direct price lookup
            rate = get_current_price(f"{from_currency}/USDT")
            return rate if rate > 0 else 0.0
            
        # For cross currency conversion
        else:
            # Get rates via USDT
            from_to_usdt = get_current_price(f"{from_currency}/USDT")
            to_to_usdt = get_current_price(f"{to_currency}/USDT")
            
            if from_to_usdt > 0 and to_to_usdt > 0:
                # Cross rate calculation: from → USDT → to
                return from_to_usdt / to_to_usdt
            return 0.0
            
    except Exception as e:
        logger.error(f"Error getting conversion rate from {from_currency} to {to_currency}: {str(e)}")
        return 0.0

def convert_currency(user_id, from_currency, to_currency, amount, wallet_type='spot'):
    """
    Convert currency for a user with enhanced error handling and rate fetching.
    
    Args:
        user_id: User ID
        from_currency: Source currency code
        to_currency: Target currency code
        amount: Amount to convert
        wallet_type: Wallet type ('spot', 'funding', 'futures')
    
    Returns:
        tuple: (success, message, converted_amount)
    """
    try:
        # Validate amount
        try:
            amount = float(amount)
            if amount <= 0:
                return False, "Amount must be greater than zero.", 0
        except (ValueError, TypeError):
            return False, "Invalid amount format.", 0
            
        # Check for same currency
        if from_currency == to_currency:
            return False, "Cannot convert to the same currency.", 0
            
        # Get user's wallet for source currency
        source_wallet = Wallet.query.filter_by(user_id=user_id, currency=from_currency).first()
        if not source_wallet:
            return False, f"No {from_currency} wallet found.", 0
            
        # Check balance based on wallet_type
        if wallet_type == 'spot':
            balance = float(source_wallet.spot_balance or 0.0)
        elif wallet_type == 'funding':
            balance = float(source_wallet.funding_balance or 0.0)
        else:  # futures
            balance = float(source_wallet.futures_balance or 0.0)
            
        if balance < amount:
            return False, f"Insufficient {from_currency} balance in {wallet_type} wallet.", 0
            
        # Get real-time conversion rate
        rate = get_conversion_rate(from_currency, to_currency)
        if rate <= 0:
            return False, f"Could not get valid conversion rate from {from_currency} to {to_currency}.", 0
            
        # Calculate converted amount
        converted_amount = amount * rate
        if converted_amount <= 0:
            return False, "Conversion resulted in zero or negative amount.", 0
            
        # Log before transaction
        logger.info(f"Converting {amount} {from_currency} to {to_currency} at rate {rate} = {converted_amount} {to_currency}")
        
        # Perform the conversion
        
        # 1. Subtract from source wallet
        success, message, _ = subtract_balance(user_id, from_currency, amount, wallet_type)
        if not success:
            return False, message, 0
            
        # 2. Add to destination wallet or create if it doesn't exist
        destination_wallet = Wallet.query.filter_by(user_id=user_id, currency=to_currency).first()
        if not destination_wallet:
            destination_wallet = create_wallet(user_id, to_currency)
            
        # 3. Add converted amount to destination wallet (same wallet type)
        add_balance(user_id, to_currency, converted_amount, wallet_type)
        
        # 4. Create conversion transaction record for tracking
        transaction = Transaction(
            user_id=user_id,
            transaction_type='convert',
            status='completed',
            currency=from_currency,
            amount=amount,
            fee=0,  # No fee for conversions
            from_wallet=wallet_type,
            to_wallet=wallet_type,
            notes=f"Converted {amount} {from_currency} to {converted_amount:.8f} {to_currency} at rate {rate:.8f}"
        )
        
        db.session.add(transaction)
        db.session.commit()
        
        return True, "Conversion completed successfully.", converted_amount
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error during currency conversion: {str(e)}")
        return False, f"Error during conversion: {str(e)}", 0

def create_deposit_transaction(user_id, currency, amount, chain, blockchain_txid=None):
    """
    Create a deposit transaction record.
    
    Returns the created transaction.
    """
    transaction = Transaction(
        user_id=user_id,
        transaction_type='deposit',
        status='pending',  # Will be updated to 'completed' after admin verification
        currency=currency,
        amount=amount,
        fee=0,  # No fee for deposits
        from_wallet='external',
        to_wallet='spot',
        chain=chain,
        blockchain_txid=blockchain_txid
    )
    
    db.session.add(transaction)
    db.session.commit()
    
    return transaction

def create_withdrawal_transaction(user_id, currency, amount, address, chain, fee=None):
    """
    Create a withdrawal transaction record.
    
    Returns the created transaction.
    """
    # Calculate fee if not provided (7% of withdrawal amount)
    if fee is None:
        fee = amount * 0.07
    
    transaction = Transaction(
        user_id=user_id,
        transaction_type='withdrawal',
        status='pending',  # Will be updated to 'completed' after admin verification
        currency=currency,
        amount=amount,
        fee=fee,
        from_wallet='spot',
        to_wallet='external',
        address=address,
        chain=chain
    )
    
    db.session.add(transaction)
    db.session.commit()
    
    return transaction

def create_transfer_transaction(user_id, currency, amount, from_wallet, to_wallet):
    """
    Create a transfer transaction record for moving funds between wallets.
    
    Returns the created transaction.
    """
    transaction = Transaction(
        user_id=user_id,
        transaction_type='transfer',
        status='completed',  # Transfers are completed immediately
        currency=currency,
        amount=amount,
        fee=0,  # No fee for internal transfers
        from_wallet=from_wallet,
        to_wallet=to_wallet
    )
    
    db.session.add(transaction)
    db.session.commit()
    
    return transaction

def create_convert_transaction(user_id, from_currency, to_currency, amount, converted_amount, rate):
    """
    Create a conversion transaction record.
    
    Returns the created transaction.
    """
    transaction = Transaction(
        user_id=user_id,
        transaction_type='convert',
        status='completed',  # Conversions are completed immediately
        currency=from_currency,
        amount=amount,
        fee=0,  # No fee for conversions
        from_wallet='spot',
        to_wallet='spot',
        notes=f"Converted {amount} {from_currency} to {converted_amount} {to_currency} at rate {rate}"
    )
    
    db.session.add(transaction)
    db.session.commit()
    
    return transaction

def create_payment_transactions(sender_id, recipient_id, currency, amount):
    """
    Create payment transaction records for both sender and recipient.
    
    Returns a tuple of (sender_transaction, recipient_transaction).
    """
    sender = User.query.get(sender_id)
    recipient = User.query.get(recipient_id)
    
    # Create transaction for sender (negative amount)
    sender_transaction = Transaction(
        user_id=sender_id,
        transaction_type='pay',
        status='completed',  # Payments are completed immediately
        currency=currency,
        amount=-amount,  # Negative amount for sender
        fee=0,  # No fee for payments
        from_wallet='spot',
        to_wallet='external',
        address=recipient.unique_id,
        notes=f"Payment to {recipient.username} ({recipient.unique_id})"
    )
    
    # Create transaction for recipient (positive amount)
    recipient_transaction = Transaction(
        user_id=recipient_id,
        transaction_type='pay',
        status='completed',  # Payments are completed immediately
        currency=currency,
        amount=amount,  # Positive amount for recipient
        fee=0,  # No fee for payments
        from_wallet='external',
        to_wallet='spot',
        address=sender.unique_id,
        notes=f"Payment from {sender.username} ({sender.unique_id})"
    )
    
    db.session.add(sender_transaction)
    db.session.add(recipient_transaction)
    db.session.commit()
    
    return sender_transaction, recipient_transaction

def get_transaction_history(user_id, transaction_type=None, limit=20, offset=0):
    """
    Get transaction history for a user.
    
    Returns a list of transactions.
    """
    query = Transaction.query.filter_by(user_id=user_id)
    
    if transaction_type:
        query = query.filter_by(transaction_type=transaction_type)
    
    transactions = query.order_by(Transaction.created_at.desc()).offset(offset).limit(limit).all()
    
    return transactions

def get_deposit_address(currency, network):
    """
    Get the deposit address for a specific currency and network.
    Uses the admin-configured addresses from the database.
    
    Args:
        currency: Currency code (e.g., 'BTC', 'USDT')
        network: Network (e.g., 'BTC', 'TRC20', 'ERC20')
    
    Returns:
        Tuple of (address_string, qr_code_path) or (None, None) if not configured
    """
    try:
        from app.models.deposit_address import DepositAddress
        
        # Query for the active address for this currency and network
        address_obj = DepositAddress.query.filter_by(
            currency=currency,
            network=network,
            is_active=True
        ).first()
        
        if address_obj:
            return address_obj.address, address_obj.qr_code_path
        
        # If no address is configured, return None
        return None, None
    except Exception as e:
        logger.error(f"Error getting deposit address for {currency} on {network}: {str(e)}")
        return None, None

def verify_deposit(transaction_id, admin_notes=None):
    """
    Verify a deposit transaction and add funds to the user's wallet.
    
    Returns a tuple of (success, message).
    """
    transaction = Transaction.query.get(transaction_id)
    
    if not transaction:
        return False, "Transaction not found."
    
    if transaction.transaction_type != 'deposit':
        return False, "Transaction is not a deposit."
    
    if transaction.status != 'pending':
        return False, "Transaction is not pending."
    
    # Update transaction status
    transaction.status = 'completed'
    transaction.admin_notes = admin_notes
    transaction.updated_at = datetime.utcnow()
    
    # Add funds to user's wallet
    wallet = Wallet.query.filter_by(user_id=transaction.user_id, currency=transaction.currency).first()
    
    if not wallet:
        wallet = Wallet(user_id=transaction.user_id, currency=transaction.currency, spot_balance=0)
        db.session.add(wallet)
    
    wallet.spot_balance += transaction.amount
    
    db.session.commit()
    
    return True, "Deposit verified successfully."

def process_withdrawal(transaction_id, blockchain_txid=None, admin_notes=None, reject=False):
    """
    Process a withdrawal transaction.
    
    If reject is True, the transaction is rejected and funds are returned to the user's wallet.
    Otherwise, the transaction is approved and marked as completed.
    
    Returns a tuple of (success, message).
    """
    transaction = Transaction.query.get(transaction_id)
    
    if not transaction:
        return False, "Transaction not found."
    
    if transaction.transaction_type != 'withdrawal':
        return False, "Transaction is not a withdrawal."
    
    if transaction.status != 'pending':
        return False, "Transaction is not pending."
    
    if reject:
        # Reject withdrawal and return funds
        transaction.status = 'failed'
        transaction.admin_notes = admin_notes
        transaction.updated_at = datetime.utcnow()
        
        # Return funds to user's wallet (amount + fee)
        wallet = Wallet.query.filter_by(user_id=transaction.user_id, currency=transaction.currency).first()
        
        if wallet:
            wallet.spot_balance += transaction.amount + transaction.fee
        
        db.session.commit()
        
        return True, "Withdrawal rejected successfully."
    else:
        # Approve withdrawal
        transaction.status = 'completed'
        transaction.blockchain_txid = blockchain_txid
        transaction.admin_notes = admin_notes
        transaction.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return True, "Withdrawal processed successfully."

def get_user_portfolio(user_id):
    """
    Get a user's portfolio with equivalent values in USDT using real-time rates.
    
    Args:
        user_id: User ID
    
    Returns:
        dict: Portfolio data with spot, funding, futures balances and total values
    """
    try:
        wallets = Wallet.query.filter_by(user_id=user_id).all()
        
        portfolio = {
            'spot': {},
            'funding': {},
            'futures': {},
            'total_spot_value': 0,
            'total_funding_value': 0,
            'total_futures_value': 0,
            'total_value': 0
        }
        
        for wallet in wallets:
            # Get safe numeric values, replacing None with 0
            spot_balance = float(wallet.spot_balance or 0)
            funding_balance = float(wallet.funding_balance or 0)
            futures_balance = float(wallet.futures_balance or 0)
            
            # Skip entirely empty wallets
            if spot_balance == 0 and funding_balance == 0 and futures_balance == 0:
                continue
            
            # Get rate from currency to USDT (real-time rate)
            if wallet.currency == 'USDT':
                rate = 1.0
            else:
                rate = get_conversion_rate(wallet.currency, 'USDT')
                if rate <= 0:
                    # Log warning and use a fallback method if available
                    logger.warning(f"Could not get rate for {wallet.currency}/USDT, using fallback")
                    
                    # Try alternative approach to get rate
                    try:
                        coin_details = get_coin_details(wallet.currency)
                        # Assuming current_price is in USD/USDT
                        if coin_details and 'current_price' in coin_details and coin_details['current_price'] > 0:
                            rate = coin_details['current_price']
                        else:
                            # Default fallback rates if all else fails
                            fallback_rates = {
                                'BTC': 60000.0,
                                'ETH': 3000.0,
                                'BNB': 500.0,
                                'XRP': 0.5,
                                'DOGE': 0.1,
                                'SOL': 100.0,
                                'ADA': 0.5,
                                'MATIC': 1.0,
                                'DOT': 20.0,
                                'AVAX': 30.0
                            }
                            rate = fallback_rates.get(wallet.currency, 1.0)
                    except Exception as e:
                        logger.error(f"Error getting fallback rate for {wallet.currency}: {str(e)}")
                        rate = 1.0  # Use 1:1 as last resort
            
            # Calculate USDT values
            spot_value = spot_balance * rate
            funding_value = funding_balance * rate
            futures_value = futures_balance * rate
            
            # Add to portfolio
            portfolio['spot'][wallet.currency] = {
                'balance': spot_balance,
                'value_usdt': spot_value
            }
            
            portfolio['funding'][wallet.currency] = {
                'balance': funding_balance,
                'value_usdt': funding_value
            }
            
            portfolio['futures'][wallet.currency] = {
                'balance': futures_balance,
                'value_usdt': futures_value
            }
            
            # Add to totals
            portfolio['total_spot_value'] += spot_value
            portfolio['total_funding_value'] += funding_value
            portfolio['total_futures_value'] += futures_value
        
        # Calculate total value across all wallet types
        portfolio['total_value'] = (
            portfolio['total_spot_value'] + 
            portfolio['total_funding_value'] + 
            portfolio['total_futures_value']
        )
        
        return portfolio
    except Exception as e:
        logger.error(f"Error calculating user portfolio: {str(e)}")
        # Return empty portfolio structure with zeros
        return {
            'spot': {},
            'funding': {},
            'futures': {},
            'total_spot_value': 0,
            'total_funding_value': 0,
            'total_futures_value': 0,
            'total_value': 0,
            'error': str(e)
        }