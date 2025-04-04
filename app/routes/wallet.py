# app/routes/wallet.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, session
from flask_login import login_required, current_user
from app import db
from app.models.user import User
from app.models.wallet import Wallet
from app.models.transaction import Transaction
from app.services.wallet_service import generate_blockchain_address, validate_address
from app.utils.crypto_api import get_exchange_rates, get_current_price
import decimal
import logging
import uuid
from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user

logger = logging.getLogger(__name__)
wallet = Blueprint('wallet', __name__)



def verification_required(f):
    """Decorator to require verification for sensitive operations"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_verified:
            flash('Verification required to access this feature. Please complete your verification.', 'warning')
            return redirect(url_for('user.verification'))
        return f(*args, **kwargs)
    return decorated_function


@wallet.route('/deposit', methods=['GET'])
@login_required
@verification_required
def deposit():
    """Get deposit page with address for selected currency and chain"""
    try:
        # Get currency and chain from query parameters
        selected_currency = request.args.get('currency', 'USDT')
        
        # Set default chain based on currency
        default_chain = 'TRC20' if selected_currency == 'USDT' else 'BTC'
        selected_chain = request.args.get('chain', default_chain)
        
        # Validate currency is one of the supported options
        if selected_currency not in ['USDT', 'BTC']:
            selected_currency = 'USDT'
            
        # Validate chain is appropriate for the currency
        if selected_currency == 'USDT' and selected_chain not in ['TRC20', 'ERC20']:
            selected_chain = 'TRC20'
        elif selected_currency == 'BTC' and selected_chain not in ['BTC', 'BSC']:
            selected_chain = 'BTC'
        
        # Get deposit address from our service
        from app.services.wallet_service import get_deposit_address
        deposit_address, qr_code_path = get_deposit_address(selected_currency, selected_chain)
        
        # Get recent deposits
        recent_deposits = Transaction.query.filter_by(
            user_id=current_user.id,
            transaction_type='deposit',
            currency=selected_currency
        ).order_by(Transaction.created_at.desc()).limit(5).all()
        
        return render_template('transactions/deposit.html', 
                            title='Deposit',
                            selected_currency=selected_currency,
                            selected_chain=selected_chain,
                            deposit_address=deposit_address,
                            qr_code_path=qr_code_path,
                            recent_deposits=recent_deposits)
    except Exception as e:
        logger.error(f"Error loading deposit page: {str(e)}")
        flash(f'Error loading deposit page: {str(e)}', 'danger')
        return redirect(url_for('user.home'))

@wallet.route('/submit-deposit', methods=['POST'])
@login_required
def submit_deposit():
    """Handle user deposit submission"""
    try:
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
            if amount <= 0:
                flash(f'Amount must be greater than 0.', 'danger')
                return redirect(url_for('wallet.deposit', currency=currency, chain=chain))
                
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
    except Exception as e:
        db.session.rollback()
        flash(f'Error processing deposit: {str(e)}', 'danger')
        return redirect(url_for('wallet.deposit', currency=currency, chain=chain))

@wallet.route('/withdraw', methods=['GET', 'POST'])
@login_required
@verification_required
def withdraw():
    """Handle withdrawal requests"""
    try:
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
                if amount <= 0:
                    flash(f'Amount must be greater than 0.', 'danger')
                    return redirect(url_for('wallet.withdraw', currency=currency, chain=chain))
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
    except Exception as e:
        db.session.rollback()
        flash(f'Error processing withdrawal: {str(e)}', 'danger')
        return redirect(url_for('user.home'))

@wallet.route('/convert', methods=['GET', 'POST'])
@login_required
@verification_required
def convert():
    """Handle currency conversion with improved real-time rate fetching"""
    try:
        # Get available currencies from existing wallets in the system
        available_currencies = db.session.query(Wallet.currency).distinct().all()
        currencies = [c[0] for c in available_currencies]
        
        # Ensure we have at least the major currencies available
        default_currencies = ['USDT', 'BTC', 'ETH', 'BNB', 'XRP']
        for currency in default_currencies:
            if currency not in currencies:
                currencies.append(currency)
        
        # Default currencies for the form
        from_currency = request.args.get('from_curr', 'USDT')
        to_currency = request.args.get('to_curr', 'BTC')
        
        # Get user's wallet balances
        wallets = Wallet.query.filter_by(user_id=current_user.id).all()
        balances = {wallet.currency: {
            'spot': float(wallet.spot_balance or 0),
            'funding': float(wallet.funding_balance or 0),
            'futures': float(wallet.futures_balance or 0)
        } for wallet in wallets}
        
        if request.method == 'POST':
            from_currency = request.form.get('from_currency')
            to_currency = request.form.get('to_currency')
            amount = request.form.get('amount')
            wallet_type = request.form.get('wallet_type', 'spot')  # Default to spot if not specified
            
            # Validate input
            if not from_currency or not to_currency or not amount:
                flash('All fields are required.', 'danger')
                return redirect(url_for('wallet.convert', from_curr=from_currency, to_curr=to_currency))
            
            try:
                amount = float(amount)
                if amount <= 0:
                    flash(f'Amount must be greater than 0.', 'danger')
                    return redirect(url_for('wallet.convert', from_curr=from_currency, to_curr=to_currency))
            except ValueError:
                flash('Invalid amount.', 'danger')
                return redirect(url_for('wallet.convert', from_curr=from_currency, to_curr=to_currency))
            
            # Check if from_currency and to_currency are different
            if from_currency == to_currency:
                flash('Cannot convert to the same currency.', 'danger')
                return redirect(url_for('wallet.convert', from_curr=from_currency, to_curr=to_currency))
            
            # Use the enhanced convert_currency function from wallet_service.py
            from app.services.wallet_service import convert_currency
            success, message, converted_amount = convert_currency(
                current_user.id, 
                from_currency, 
                to_currency, 
                amount,
                wallet_type
            )
            
            if success:
                flash(f'Successfully converted {amount} {from_currency} to {converted_amount:.8f} {to_currency}!', 'success')
            else:
                flash(f'Error: {message}', 'danger')
                
            return redirect(url_for('wallet.convert', from_curr=from_currency, to_curr=to_currency))
        
        # Get recent conversions
        recent_conversions = Transaction.query.filter_by(
            user_id=current_user.id,
            transaction_type='convert'
        ).order_by(Transaction.created_at.desc()).limit(5).all()
        
        # Get current conversion rate
        from app.services.wallet_service import get_conversion_rate
        current_rate = get_conversion_rate(from_currency, to_currency)
        
        return render_template('transactions/convert.html', 
                          title='Convert', 
                          currencies=currencies,
                          from_currency=from_currency,
                          to_currency=to_currency,
                          balances=balances,
                          current_rate=current_rate,
                          recent_conversions=recent_conversions)
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error processing conversion: {str(e)}")
        flash(f'Error processing conversion: {str(e)}', 'danger')
        return redirect(url_for('user.home'))

@wallet.route('/transfer', methods=['GET', 'POST'])
@login_required
@verification_required
def transfer():
    """Handle transfers between spot, funding, and futures wallets"""
    try:
        # Get available currencies
        currencies = ['USDT', 'BTC', 'ETH', 'BNB', 'XRP']  # TODO: Get from DB or API
        
        # Default currency
        selected_currency = request.args.get('currency', 'USDT')
        
        # Get user's wallet balances
        wallets = Wallet.query.filter_by(user_id=current_user.id).all()
        balances = {}
        
        for wallet in wallets:
            if wallet.currency not in balances:
                balances[wallet.currency] = {'spot': 0, 'funding': 0, 'futures': 0}
            
            balances[wallet.currency]['spot'] = wallet.spot_balance
            balances[wallet.currency]['funding'] = wallet.funding_balance
            balances[wallet.currency]['futures'] = wallet.futures_balance
        
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
                if amount <= 0:
                    flash(f'Amount must be greater than 0.', 'danger')
                    return redirect(url_for('wallet.transfer', currency=currency))
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
            elif from_wallet == 'futures' and user_wallet.futures_balance < amount:
                flash('Insufficient futures balance.', 'danger')
                return redirect(url_for('wallet.transfer', currency=currency))
            
            # Perform transfer based on source and destination
            if from_wallet == 'spot':
                user_wallet.spot_balance -= amount
                if to_wallet == 'funding':
                    user_wallet.funding_balance += amount
                else:  # to_wallet == 'futures'
                    user_wallet.futures_balance += amount
            elif from_wallet == 'funding':
                user_wallet.funding_balance -= amount
                if to_wallet == 'spot':
                    user_wallet.spot_balance += amount
                else:  # to_wallet == 'futures'
                    user_wallet.futures_balance += amount
            else:  # from_wallet == 'futures'
                user_wallet.futures_balance -= amount
                if to_wallet == 'spot':
                    user_wallet.spot_balance += amount
                else:  # to_wallet == 'funding'
                    user_wallet.funding_balance += amount
            
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
    except Exception as e:
        db.session.rollback()
        flash(f'Error processing transfer: {str(e)}', 'danger')
        return redirect(url_for('user.home'))

@wallet.route('/pay', methods=['GET', 'POST'])
@login_required
@verification_required
def pay():
    """Handle peer-to-peer payments between users"""
    try:
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
                if amount <= 0:
                    flash(f'Amount must be greater than 0.', 'danger')
                    return redirect(url_for('wallet.pay', currency=currency))
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
    except Exception as e:
        db.session.rollback()
        flash(f'Error processing payment: {str(e)}', 'danger')
        return redirect(url_for('user.home'))

@wallet.route('/verify-recipient', methods=['POST'])
@login_required
def verify_recipient():
    """API endpoint to verify recipient information"""
    try:
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
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error verifying recipient: {str(e)}'})

@wallet.route('/get-conversion-rate', methods=['GET'])
@login_required
def get_conversion_rate_api():
    """API endpoint to get current conversion rate between currencies"""
    try:
        from_currency = request.args.get('from')
        to_currency = request.args.get('to')
        
        if not from_currency or not to_currency:
            return jsonify({'success': False, 'message': 'Both from and to currencies are required.'})
        
        # Get real-time conversion rate
        from app.services.wallet_service import get_conversion_rate
        rate = get_conversion_rate(from_currency, to_currency)
        
        if rate <= 0:
            return jsonify({
                'success': False, 
                'message': 'Could not get a valid conversion rate for this pair.',
                'from_currency': from_currency,
                'to_currency': to_currency,
                'rate': 0
            })
        
        return jsonify({
            'success': True,
            'from_currency': from_currency,
            'to_currency': to_currency,
            'rate': rate
        })
    except Exception as e:
        logger.error(f"Error getting conversion rate: {str(e)}")
        return jsonify({
            'success': False, 
            'message': f'Error getting conversion rate: {str(e)}',
            'from_currency': from_currency if 'from_currency' in locals() else None,
            'to_currency': to_currency if 'to_currency' in locals() else None,
            'rate': 0
        })

@wallet.route('/convert/preview', methods=['POST'])
@login_required
def preview_conversion():
    """API endpoint to preview a conversion without executing it"""
    try:
        data = request.get_json()
        
        from_currency = data.get('from_currency')
        to_currency = data.get('to_currency')
        amount = data.get('amount')
        wallet_type = data.get('wallet_type', 'spot')
        
        # Validate inputs
        if not from_currency or not to_currency or not amount:
            return jsonify({'success': False, 'message': 'Missing required parameters'})
            
        try:
            amount = float(amount)
            if amount <= 0:
                return jsonify({'success': False, 'message': 'Amount must be greater than zero'})
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': 'Invalid amount format'})
            
        if from_currency == to_currency:
            return jsonify({'success': False, 'message': 'Cannot convert to the same currency'})
            
        # Check wallet balance
        user_wallet = Wallet.query.filter_by(user_id=current_user.id, currency=from_currency).first()
        available_balance = 0
        
        if user_wallet:
            if wallet_type == 'spot':
                available_balance = float(user_wallet.spot_balance or 0)
            elif wallet_type == 'funding':
                available_balance = float(user_wallet.funding_balance or 0)
            else:  # futures
                available_balance = float(user_wallet.futures_balance or 0)
        
        if amount > available_balance:
            return jsonify({
                'success': False, 
                'message': f'Insufficient balance. Available: {available_balance} {from_currency}'
            })
            
        # Get conversion rate
        from app.services.wallet_service import get_conversion_rate
        rate = get_conversion_rate(from_currency, to_currency)
        
        if rate <= 0:
            return jsonify({
                'success': False, 
                'message': f'Could not get a valid conversion rate from {from_currency} to {to_currency}'
            })
            
        # Calculate converted amount
        converted_amount = amount * rate
        
        return jsonify({
            'success': True,
            'from_currency': from_currency,
            'to_currency': to_currency,
            'amount': amount,
            'converted_amount': converted_amount,
            'rate': rate,
            'wallet_type': wallet_type,
            'available_balance': available_balance
        })
        
    except Exception as e:
        logger.error(f"Error previewing conversion: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})
    

# Add this route to your wallet.py file

@wallet.route('/get-balance', methods=['GET'])
@login_required
def get_balance():
    """API endpoint to get wallet balance for a specific wallet type and currency"""
    try:
        wallet_type = request.args.get('type', 'spot')
        currency = request.args.get('currency', 'USDT')
        
        # Get the wallet
        wallet = Wallet.query.filter_by(user_id=current_user.id, currency=currency).first()
        
        # Default balance to 0 if wallet doesn't exist
        balance = 0
        
        if wallet:
            if wallet_type == 'futures':
                # Safely handle futures_balance which might be None
                balance = wallet.futures_balance if hasattr(wallet, 'futures_balance') and wallet.futures_balance is not None else 0
            elif wallet_type == 'funding':
                balance = wallet.funding_balance if wallet.funding_balance is not None else 0
            else:  # Default to spot
                balance = wallet.spot_balance if wallet.spot_balance is not None else 0
        
        # Ensure balance is a float
        balance = float(balance)
        
        # Return the balance
        return jsonify({
            'success': True,
            'balance': balance,
            'currency': currency,
            'wallet_type': wallet_type
        })
    except Exception as e:
        logger.error(f"Error getting wallet balance: {str(e)}")
        return jsonify({
            'success': False, 
            'message': f"Error getting wallet balance: {str(e)}",
            'balance': 0
        })