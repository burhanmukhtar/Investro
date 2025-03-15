# app/services/wallet_service.py
import random
import string
import re
from datetime import datetime
from app import db
from app.models.wallet import Wallet
from app.models.transaction import Transaction
from app.models.user import User


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

def get_wallet_balance(user_id, currency):
    """
    Get the wallet balance for a user and currency.
    
    Returns a tuple of (spot_balance, funding_balance).
    """
    wallet = Wallet.query.filter_by(user_id=user_id, currency=currency).first()
    
    if wallet:
        return wallet.spot_balance, wallet.funding_balance
    else:
        return 0, 0

def create_wallet(user_id, currency):
    """
    Create a new wallet for a user and currency.
    
    Returns the created wallet.
    """
    wallet = Wallet(
        user_id=user_id,
        currency=currency,
        spot_balance=0,
        funding_balance=0
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
    
    if wallet_type == 'spot':
        wallet.spot_balance += amount
    else:  # wallet_type == 'funding'
        wallet.funding_balance += amount
    
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
    
    if wallet_type == 'spot':
        if wallet.spot_balance < amount:
            return False, "Insufficient balance.", wallet
        wallet.spot_balance -= amount
    else:  # wallet_type == 'funding'
        if wallet.funding_balance < amount:
            return False, "Insufficient balance.", wallet
        wallet.funding_balance -= amount
    
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

def convert_currency(user_id, from_currency, to_currency, amount, rate):
    """
    Convert currency for a user.
    
    Returns a tuple of (success, message, converted_amount).
    """
    # Subtract from source currency
    success, message, source_wallet = subtract_balance(user_id, from_currency, amount)
    
    if not success:
        return False, message, 0
    
    # Calculate converted amount
    converted_amount = amount * rate
    
    # Add to destination currency
    add_balance(user_id, to_currency, converted_amount)
    
    return True, "Conversion completed successfully.", converted_amount

def get_conversion_rate(from_currency, to_currency):
    """
    Get the conversion rate between two currencies.
    
    This is a placeholder function. In a real implementation, you would integrate
    with a cryptocurrency API to get actual exchange rates.
    
    For development, this returns a mock rate.
    """
    # Mock conversion rates
    rates = {
        'USDT_BTC': 0.000037,
        'USDT_ETH': 0.00048,
        'USDT_BNB': 0.0042,
        'USDT_XRP': 2.3,
        'BTC_USDT': 27000,
        'BTC_ETH': 13,
        'BTC_BNB': 113,
        'BTC_XRP': 62000,
        'ETH_USDT': 2080,
        'ETH_BTC': 0.077,
        'ETH_BNB': 8.7,
        'ETH_XRP': 4800,
        'BNB_USDT': 238,
        'BNB_BTC': 0.0088,
        'BNB_ETH': 0.115,
        'BNB_XRP': 550,
        'XRP_USDT': 0.435,
        'XRP_BTC': 0.000016,
        'XRP_ETH': 0.00021,
        'XRP_BNB': 0.0018
    }
    
    rate_key = f"{from_currency}_{to_currency}"
    if rate_key in rates:
        return rates[rate_key]
    else:
        return 1  # Default
    
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
    Create a transfer transaction record for moving funds between spot and funding wallets.
    
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
        fee=0,  # No fee for conversions (spread is built into the rate)
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

def get_deposit_address(user_id, currency, chain):
    """
    Get a deposit address for a user.
    
    This is a placeholder function. In a real implementation, you would integrate
    with a cryptocurrency wallet or node to generate or retrieve actual blockchain addresses.
    
    For development, this generates a mock address that is consistent for each user, currency, and chain.
    """
    # Generate a consistent mock address based on user_id, currency, and chain
    seed = f"{user_id}_{currency}_{chain}"
    random.seed(seed)
    
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
    Get a user's portfolio with equivalent values in USDT.
    
    Returns a dict with portfolio data.
    """
    wallets = Wallet.query.filter_by(user_id=user_id).all()
    
    portfolio = {
        'spot': {},
        'funding': {},
        'total_spot_value': 0,
        'total_funding_value': 0,
        'total_value': 0
    }
    
    for wallet in wallets:
        # Skip empty wallets
        if wallet.spot_balance == 0 and wallet.funding_balance == 0:
            continue
        
        # Get equivalent value in USDT
        if wallet.currency == 'USDT':
            rate = 1
        else:
            rate = get_conversion_rate(wallet.currency, 'USDT')
        
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
    
    return portfolio    