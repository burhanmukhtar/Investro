# app/routes/wallet.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, session
from flask_login import login_required, current_user
from app import db, bcrypt
from app.models.user import User
from app.models.wallet import Wallet
from app.models.transaction import Transaction
from app.services.wallet_service import generate_blockchain_address, validate_address
import decimal
import uuid

wallet = Blueprint('wallet', __name__)

@wallet.route('/deposit')
@login_required
def deposit():
    # Get available currencies
    currencies = ['USDT', 'BTC', 'ETH', 'BNB', 'XRP']  # TODO: Get from DB or API
    
    # Default currency
    selected_currency = request.args.get('currency', 'USDT')
    selected_chain = request.args.get('chain', 'TRC20')
    
    # Get deposit address for the selected currency and chain
    deposit_address = generate_blockchain_address(current_user.id, selected_currency, selected_chain)
    
    # Get recent deposits
    recent_deposits = Transaction.query.filter_by(
        user_id=current_user.id,
        transaction_type='deposit',
        currency=selected_currency
    ).order_by(Transaction.created_at.desc()).limit(5).all()
    
    return render_template('transactions/deposit.html', 
                          title='Deposit', 
                          currencies=currencies,
                          selected_currency=selected_currency,
                          selected_chain=selected_chain,
                          deposit_address=deposit_address,
                          recent_deposits=recent_deposits)


@wallet.route('/submit-deposit', methods=['POST'])
@login_required
def submit_deposit():
    """Handle user deposit submission"""
    currency = request.form.get('currency')
    chain = request.form.get('chain')
    amount = request.form.get('amount')
    blockchain_txid = request.form.get('blockchain_txid')
    
    # Validate input
    if not currency or not chain or not amount or not blockchain_txid:
        flash('All fields are required.', 'danger')
        return redirect(url_for('wallet.deposit', currency=currency, chain=chain))
    
    try:
        amount = float(amount)
        if amount < 10:
            flash(f'Minimum deposit amount is 10 {currency}.', 'danger')
            return redirect(url_for('wallet.deposit', currency=currency, chain=chain))
    except ValueError:
        flash('Invalid amount.', 'danger')
        return redirect(url_for('wallet.deposit', currency=currency, chain=chain))
    
    # Check if transaction ID has already been used
    existing_tx = Transaction.query.filter_by(blockchain_txid=blockchain_txid).first()
    if existing_tx:
        flash('This transaction ID has already been submitted.', 'danger')
        return redirect(url_for('wallet.deposit', currency=currency, chain=chain))
    
    # Create deposit transaction
    transaction = Transaction(
        user_id=current_user.id,
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
    
    flash('Deposit submitted successfully! It will be processed after admin verification.', 'success')
    return redirect(url_for('wallet.deposit', currency=currency, chain=chain))

@wallet.route('/withdraw', methods=['GET', 'POST'])
@login_required
def withdraw():
    # Get available currencies
    currencies = ['USDT', 'BTC', 'ETH', 'BNB', 'XRP']  # TODO: Get from DB or API
    
    # Default currency
    selected_currency = request.args.get('currency', 'USDT')
    selected_chain = request.args.get('chain', 'TRC20')
    
    # Get user's wallet balance
    wallet = Wallet.query.filter_by(user_id=current_user.id, currency=selected_currency).first()
    balance = 0
    if wallet:
        balance = wallet.spot_balance
    
    if request.method == 'POST':
        address = request.form.get('address')
        amount = request.form.get('amount')
        chain = request.form.get('chain')
        currency = request.form.get('currency')
        withdrawal_pin = request.form.get('withdrawal_pin')
        
        # Validate input
        if not address or not amount or not chain or not currency or not withdrawal_pin:
            flash('All fields are required.', 'danger')
            return redirect(url_for('wallet.withdraw', currency=currency, chain=chain))
        
        try:
            amount = float(amount)
        except ValueError:
            flash('Invalid amount.', 'danger')
            return redirect(url_for('wallet.withdraw', currency=currency, chain=chain))
        
        # Check if user has set withdrawal PIN
        if not current_user.withdrawal_pin_hash:
            flash('Please set a withdrawal PIN in your profile settings.', 'danger')
            return redirect(url_for('wallet.withdraw', currency=currency, chain=chain))
        
        # Verify withdrawal PIN
        if not current_user.check_withdrawal_pin(withdrawal_pin):
            flash('Invalid withdrawal PIN.', 'danger')
            return redirect(url_for('wallet.withdraw', currency=currency, chain=chain))
        
        # Check if address is valid
        if not validate_address(address, currency, chain):
            flash('Invalid withdrawal address.', 'danger')
            return redirect(url_for('wallet.withdraw', currency=currency, chain=chain))
        
        # Check if user has enough balance
        user_wallet = Wallet.query.filter_by(user_id=current_user.id, currency=currency).first()
        if not user_wallet or user_wallet.spot_balance < amount:
            flash('Insufficient balance.', 'danger')
            return redirect(url_for('wallet.withdraw', currency=currency, chain=chain))
        
        # Calculate fee (7% of withdrawal amount)
        fee = amount * 0.07
        total_deduction = amount + fee
        
        if user_wallet.spot_balance < total_deduction:
            flash(f'Insufficient balance to cover withdrawal amount plus fee ({fee} {currency}).', 'danger')
            return redirect(url_for('wallet.withdraw', currency=currency, chain=chain))
        
        # Create withdrawal transaction
        transaction = Transaction(
            user_id=current_user.id,
            transaction_type='withdrawal',
            status='pending',
            currency=currency,
            amount=amount,
            fee=fee,
            from_wallet='spot',
            to_wallet='external',
            address=address,
            chain=chain
        )
        
        # Deduct balance from user's wallet
        user_wallet.spot_balance -= total_deduction
        
        db.session.add(transaction)
        db.session.commit()
        
        flash('Withdrawal request submitted successfully!', 'success')
        return redirect(url_for('wallet.withdraw', currency=currency, chain=chain))
    
    # Get recent withdrawals
    recent_withdrawals = Transaction.query.filter_by(
        user_id=current_user.id,
        transaction_type='withdrawal',
        currency=selected_currency
    ).order_by(Transaction.created_at.desc()).limit(5).all()
    
    return render_template('transactions/withdraw.html', 
                          title='Withdraw', 
                          currencies=currencies,
                          selected_currency=selected_currency,
                          selected_chain=selected_chain,
                          balance=balance,
                          recent_withdrawals=recent_withdrawals)

@wallet.route('/convert', methods=['GET', 'POST'])
@login_required
def convert():
    # Get available currencies
    currencies = ['USDT', 'BTC', 'ETH', 'BNB', 'XRP']  # TODO: Get from DB or API
    
    # Default currencies - Fix: change 'from' to 'from_curr'
    from_currency = request.args.get('from_curr', 'USDT')
    to_currency = request.args.get('to_curr', 'BTC')
    
    # Get user's wallet balances
    wallets = Wallet.query.filter_by(user_id=current_user.id).all()
    balances = {wallet.currency: wallet.spot_balance for wallet in wallets}
    
    if request.method == 'POST':
        from_currency = request.form.get('from_currency')
        to_currency = request.form.get('to_currency')
        amount = request.form.get('amount')
        
        # Validate input
        if not from_currency or not to_currency or not amount:
            flash('All fields are required.', 'danger')
            # Fix: change 'from' to 'from_curr'
            return redirect(url_for('wallet.convert', from_curr=from_currency, to_curr=to_currency))
        
        try:
            amount = float(amount)
        except ValueError:
            flash('Invalid amount.', 'danger')
            # Fix: change 'from' to 'from_curr'
            return redirect(url_for('wallet.convert', from_curr=from_currency, to_curr=to_currency))
        
        # Check if user has enough balance
        from_wallet = Wallet.query.filter_by(user_id=current_user.id, currency=from_currency).first()
        if not from_wallet or from_wallet.spot_balance < amount:
            flash('Insufficient balance.', 'danger')
            # Fix: change 'from' to 'from_curr'
            return redirect(url_for('wallet.convert', from_curr=from_currency, to_curr=to_currency))
        
        # TODO: Get conversion rate from API
        # For now, use dummy rates
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
            rate = rates[rate_key]
        else:
            flash('Conversion rate not available for the selected pair.', 'danger')
            # Fix: change 'from' to 'from_curr'
            return redirect(url_for('wallet.convert', from_curr=from_currency, to_curr=to_currency))
        
        # Calculate converted amount
        converted_amount = amount * rate
        
        # Deduct from source wallet
        from_wallet.spot_balance -= amount
        
        # Add to destination wallet
        to_wallet = Wallet.query.filter_by(user_id=current_user.id, currency=to_currency).first()
        if not to_wallet:
            to_wallet = Wallet(user_id=current_user.id, currency=to_currency, spot_balance=0)
            db.session.add(to_wallet)
        
        to_wallet.spot_balance += converted_amount
        
        # Create conversion transaction
        transaction = Transaction(
            user_id=current_user.id,
            transaction_type='convert',
            status='completed',
            currency=from_currency,
            amount=amount,
            fee=0,
            from_wallet='spot',
            to_wallet='spot',
            notes=f"Converted {amount} {from_currency} to {converted_amount} {to_currency} at rate {rate}"
        )
        
        db.session.add(transaction)
        db.session.commit()
        
        flash(f'Successfully converted {amount} {from_currency} to {converted_amount:.8f} {to_currency}!', 'success')
        # Fix: change 'from' to 'from_curr'
        return redirect(url_for('wallet.convert', from_curr=from_currency, to_curr=to_currency))
    
    # Get recent conversions
    recent_conversions = Transaction.query.filter_by(
        user_id=current_user.id,
        transaction_type='convert'
    ).order_by(Transaction.created_at.desc()).limit(5).all()
    
    return render_template('transactions/convert.html', 
                          title='Convert', 
                          currencies=currencies,
                          from_currency=from_currency,
                          to_currency=to_currency,
                          balances=balances,
                          recent_conversions=recent_conversions)

@wallet.route('/transfer', methods=['GET', 'POST'])
@login_required
def transfer():
    # Get available currencies
    currencies = ['USDT', 'BTC', 'ETH', 'BNB', 'XRP']  # TODO: Get from DB or API
    
    # Default currency
    selected_currency = request.args.get('currency', 'USDT')
    
    # Get user's wallet balances
    wallets = Wallet.query.filter_by(user_id=current_user.id).all()
    balances = {}
    
    for wallet in wallets:
        if wallet.currency not in balances:
            balances[wallet.currency] = {'spot': 0, 'funding': 0}
        
        balances[wallet.currency]['spot'] = wallet.spot_balance
        balances[wallet.currency]['funding'] = wallet.funding_balance
    
    if request.method == 'POST':
        currency = request.form.get('currency')
        amount = request.form.get('amount')
        from_wallet = request.form.get('from_wallet')
        to_wallet = request.form.get('to_wallet')
        
        # Validate input
        if not currency or not amount or not from_wallet or not to_wallet:
            flash('All fields are required.', 'danger')
            return redirect(url_for('wallet.transfer', currency=currency))
        
        try:
            amount = float(amount)
        except ValueError:
            flash('Invalid amount.', 'danger')
            return redirect(url_for('wallet.transfer', currency=currency))
        
        # Check if from_wallet and to_wallet are different
        if from_wallet == to_wallet:
            flash('Cannot transfer to the same wallet.', 'danger')
            return redirect(url_for('wallet.transfer', currency=currency))
        
        # Get user's wallet
        user_wallet = Wallet.query.filter_by(user_id=current_user.id, currency=currency).first()
        if not user_wallet:
            flash('Wallet not found.', 'danger')
            return redirect(url_for('wallet.transfer', currency=currency))
        
        # Check if user has enough balance in the source wallet
        if from_wallet == 'spot' and user_wallet.spot_balance < amount:
            flash('Insufficient spot balance.', 'danger')
            return redirect(url_for('wallet.transfer', currency=currency))
        elif from_wallet == 'funding' and user_wallet.funding_balance < amount:
            flash('Insufficient funding balance.', 'danger')
            return redirect(url_for('wallet.transfer', currency=currency))
        
        # Perform transfer
        if from_wallet == 'spot':
            user_wallet.spot_balance -= amount
            user_wallet.funding_balance += amount
        else:  # from_wallet == 'funding'
            user_wallet.funding_balance -= amount
            user_wallet.spot_balance += amount
        
        # Create transfer transaction
        transaction = Transaction(
            user_id=current_user.id,
            transaction_type='transfer',
            status='completed',
            currency=currency,
            amount=amount,
            fee=0,
            from_wallet=from_wallet,
            to_wallet=to_wallet
        )
        
        db.session.add(transaction)
        db.session.commit()
        
        flash(f'Successfully transferred {amount} {currency} from {from_wallet} to {to_wallet}!', 'success')
        return redirect(url_for('wallet.transfer', currency=currency))
    
    # Get recent transfers
    recent_transfers = Transaction.query.filter_by(
        user_id=current_user.id,
        transaction_type='transfer'
    ).order_by(Transaction.created_at.desc()).limit(5).all()
    
    return render_template('transactions/transfer.html', 
                          title='Transfer', 
                          currencies=currencies,
                          selected_currency=selected_currency,
                          balances=balances,
                          recent_transfers=recent_transfers)

@wallet.route('/pay', methods=['GET', 'POST'])
@login_required
def pay():
    # Get available currencies
    currencies = ['USDT', 'BTC', 'ETH', 'BNB', 'XRP']  # TODO: Get from DB or API
    
    # Default currency
    selected_currency = request.args.get('currency', 'USDT')
    
    # Get user's wallet balances
    wallets = Wallet.query.filter_by(user_id=current_user.id).all()
    balances = {wallet.currency: wallet.spot_balance for wallet in wallets}
    
    if request.method == 'POST':
        currency = request.form.get('currency')
        amount = request.form.get('amount')
        recipient_id = request.form.get('recipient_id')
        
        # Validate input
        if not currency or not amount or not recipient_id:
            flash('All fields are required.', 'danger')
            return redirect(url_for('wallet.pay', currency=currency))
        
        try:
            amount = float(amount)
        except ValueError:
            flash('Invalid amount.', 'danger')
            return redirect(url_for('wallet.pay', currency=currency))
        
        # Find recipient user
        recipient = User.query.filter_by(unique_id=recipient_id).first()
        if not recipient:
            flash('Recipient not found.', 'danger')
            return redirect(url_for('wallet.pay', currency=currency))
        
        # Check if user is paying themselves
        if recipient.id == current_user.id:
            flash('Cannot pay yourself.', 'danger')
            return redirect(url_for('wallet.pay', currency=currency))
        
        # Check if user has enough balance
        sender_wallet = Wallet.query.filter_by(user_id=current_user.id, currency=currency).first()
        if not sender_wallet or sender_wallet.spot_balance < amount:
            flash('Insufficient balance.', 'danger')
            return redirect(url_for('wallet.pay', currency=currency))
        
        # Get or create recipient's wallet
        recipient_wallet = Wallet.query.filter_by(user_id=recipient.id, currency=currency).first()
        if not recipient_wallet:
            recipient_wallet = Wallet(user_id=recipient.id, currency=currency, spot_balance=0)
            db.session.add(recipient_wallet)
        
        # Perform transfer
        sender_wallet.spot_balance -= amount
        recipient_wallet.spot_balance += amount
        
        # Create payment transaction for sender
        sender_transaction = Transaction(
            user_id=current_user.id,
            transaction_type='pay',
            status='completed',
            currency=currency,
            amount=-amount,  # Negative amount for sender
            fee=0,
            from_wallet='spot',
            to_wallet='external',
            address=recipient.unique_id,
            notes=f"Payment to {recipient.username} ({recipient.unique_id})"
        )
        
        # Create payment transaction for recipient
        recipient_transaction = Transaction(
            user_id=recipient.id,
            transaction_type='pay',
            status='completed',
            currency=currency,
            amount=amount,
            fee=0,
            from_wallet='external',
            to_wallet='spot',
            address=current_user.unique_id,
            notes=f"Payment from {current_user.username} ({current_user.unique_id})"
        )
        
        db.session.add(sender_transaction)
        db.session.add(recipient_transaction)
        db.session.commit()
        
        flash(f'Successfully paid {amount} {currency} to {recipient.username}!', 'success')
        return redirect(url_for('wallet.pay', currency=currency))
    
    # Get recent payments
    recent_payments = Transaction.query.filter_by(
        user_id=current_user.id,
        transaction_type='pay'
    ).order_by(Transaction.created_at.desc()).limit(5).all()
    
    return render_template('transactions/pay.html', 
                          title='Pay', 
                          currencies=currencies,
                          selected_currency=selected_currency,
                          balances=balances,
                          recent_payments=recent_payments)

@wallet.route('/verify-recipient', methods=['POST'])
@login_required
def verify_recipient():
    recipient_id = request.form.get('recipient_id')
    
    if not recipient_id:
        return jsonify({'success': False, 'message': 'Recipient ID is required.'})
    
    recipient = User.query.filter_by(unique_id=recipient_id).first()
    
    if not recipient:
        return jsonify({'success': False, 'message': 'Recipient not found.'})
    
    if recipient.id == current_user.id:
        return jsonify({'success': False, 'message': 'Cannot pay yourself.'})
    
    return jsonify({
        'success': True,
        'recipient': {
            'username': recipient.username,
            'unique_id': recipient.unique_id,
            'is_verified': recipient.is_verified
        }
    })