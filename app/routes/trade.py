

# app/routes/trade.py
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
from app.models.trade_signal import TradeSignal, TradePosition
from app.models.wallet import Wallet
from app.services.market_service import get_current_price
from datetime import datetime
from app.models.order import Order


trade = Blueprint('trade', __name__)

@trade.route('/signals')
@login_required
def signals():
    # Get active trade signals
    active_signals = TradeSignal.query.filter_by(is_active=True).order_by(TradeSignal.created_at.desc()).all()
    
    return jsonify({
        'success': True,
        'signals': [{
            'id': signal.id,
            'currency_pair': signal.currency_pair,
            'signal_type': signal.signal_type,
            'entry_price': signal.entry_price,
            'target_price': signal.target_price,
            'stop_loss': signal.stop_loss,
            'leverage': signal.leverage,
            'description': signal.description,
            'expiry_time': signal.expiry_time.isoformat(),
            'created_at': signal.created_at.isoformat()
        } for signal in active_signals]
    })

@trade.route('/follow-signal', methods=['POST'])
@login_required
def follow_signal():
    signal_id = request.form.get('signal_id')
    amount = request.form.get('amount')
    
    # Validate input
    if not signal_id or not amount:
        return jsonify({'success': False, 'message': 'Signal ID and amount are required.'})
    
    try:
        signal_id = int(signal_id)
        amount = float(amount)
    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid signal ID or amount.'})
    
    # Check if signal exists and is active
    signal = TradeSignal.query.filter_by(id=signal_id, is_active=True).first()
    if not signal:
        return jsonify({'success': False, 'message': 'Signal not found or inactive.'})
    
    # Check if user already has a position for this signal
    existing_position = TradePosition.query.filter_by(user_id=current_user.id, signal_id=signal_id, status='open').first()
    if existing_position:
        return jsonify({'success': False, 'message': 'You already have an open position for this signal.'})
    
    # Extract base currency from pair (e.g., BTC from BTC/USDT)
    base_currency = signal.currency_pair.split('/')[1]
    
    # Check if user has enough balance
    wallet = Wallet.query.filter_by(user_id=current_user.id, currency=base_currency).first()
    if not wallet or wallet.spot_balance < amount:
        return jsonify({'success': False, 'message': f'Insufficient {base_currency} balance.'})
    
    # Get current price
    current_price = get_current_price(signal.currency_pair)
    
    # Create position
    position = TradePosition(
        user_id=current_user.id,
        signal_id=signal_id,
        amount=amount,
        entry_price=current_price
    )
    
    # Deduct amount from user's wallet
    wallet.spot_balance -= amount
    
    db.session.add(position)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Successfully followed signal with {amount} {base_currency}.',
        'position': {
            'id': position.id,
            'signal_id': position.signal_id,
            'amount': position.amount,
            'entry_price': position.entry_price,
            'created_at': position.created_at.isoformat()
        }
    })

@trade.route('/positions')
@login_required
def positions():
    # Get user's open positions
    open_positions = TradePosition.query.filter_by(user_id=current_user.id, status='open').all()
    
    positions_data = []
    for position in open_positions:
        signal = TradeSignal.query.get(position.signal_id)
        
        # Get current price
        current_price = get_current_price(signal.currency_pair)
        
        # Calculate profit/loss
        if signal.signal_type == 'buy':
            profit_loss_percentage = ((current_price - position.entry_price) / position.entry_price) * 100 * signal.leverage
        else:  # signal_type == 'sell'
            profit_loss_percentage = ((position.entry_price - current_price) / position.entry_price) * 100 * signal.leverage
        
        profit_loss = position.amount * (profit_loss_percentage / 100)
        
        positions_data.append({
            'id': position.id,
            'signal_id': position.signal_id,
            'currency_pair': signal.currency_pair,
            'signal_type': signal.signal_type,
            'amount': position.amount,
            'entry_price': position.entry_price,
            'current_price': current_price,
            'profit_loss': profit_loss,
            'profit_loss_percentage': profit_loss_percentage,
            'leverage': signal.leverage,
            'target_price': signal.target_price,
            'stop_loss': signal.stop_loss,
            'created_at': position.created_at.isoformat()
        })
    
    return jsonify({
        'success': True,
        'positions': positions_data
    })

@trade.route('/close-position', methods=['POST'])
@login_required
def close_position():
    position_id = request.form.get('position_id')
    
    # Validate input
    if not position_id:
        return jsonify({'success': False, 'message': 'Position ID is required.'})
    
    try:
        position_id = int(position_id)
    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid position ID.'})
    
    # Check if position exists and belongs to user
    position = TradePosition.query.filter_by(id=position_id, user_id=current_user.id, status='open').first()
    if not position:
        return jsonify({'success': False, 'message': 'Position not found or already closed.'})
    
    # Rest of the function...
    
    # Get signal
    signal = TradeSignal.query.get(position.signal_id)
    if not signal:
        return jsonify({'success': False, 'message': 'Signal not found.'})
    
    # Extract base currency from pair (e.g., BTC from BTC/USDT)
    base_currency = signal.currency_pair.split('/')[1]
    
    # Get current price
    current_price = get_current_price(signal.currency_pair)
    
    # Calculate profit/loss
    if signal.signal_type == 'buy':
        profit_loss_percentage = ((current_price - position.entry_price) / position.entry_price) * 100 * signal.leverage
    else:  # signal_type == 'sell'
        profit_loss_percentage = ((position.entry_price - current_price) / position.entry_price) * 100 * signal.leverage
    
    profit_loss = position.amount * (profit_loss_percentage / 100)
    
    # Update position
    position.status = 'closed'
    position.close_price = current_price
    position.profit_loss = profit_loss
    position.profit_loss_percentage = profit_loss_percentage
    position.closed_at = datetime.utcnow()
    
    # Return amount + profit to user's wallet (or deduct loss)
    wallet = Wallet.query.filter_by(user_id=current_user.id, currency=base_currency).first()
    if not wallet:
        wallet = Wallet(user_id=current_user.id, currency=base_currency, spot_balance=0)
        db.session.add(wallet)
    
    # Return original amount plus profit (or minus loss)
    wallet.spot_balance += position.amount + profit_loss
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Position closed successfully. Profit/Loss: {profit_loss:.8f} {base_currency} ({profit_loss_percentage:.2f}%)',
        'position': {
            'id': position.id,
            'close_price': position.close_price,
            'profit_loss': position.profit_loss,
            'profit_loss_percentage': position.profit_loss_percentage,
            'closed_at': position.closed_at.isoformat()
        }
    })

@trade.route('/history')
@login_required
def history():
    """
    Get user's closed positions history.
    Returns JSON data for the frontend to display.
    """
    try:
        # Get user's closed positions
        closed_positions = TradePosition.query.filter_by(
            user_id=current_user.id, 
            status='closed'
        ).order_by(TradePosition.closed_at.desc()).all()
        
        positions_data = []
        for position in closed_positions:
            # Get the signal, with error handling in case signal was deleted
            signal = TradeSignal.query.get(position.signal_id)
            
            # Create position data even if signal is missing
            position_data = {
                'id': position.id,
                'signal_id': position.signal_id,
                'amount': position.amount,
                'entry_price': position.entry_price,
                'close_price': position.close_price,
                'profit_loss': position.profit_loss,
                'profit_loss_percentage': position.profit_loss_percentage,
                'created_at': position.created_at.isoformat(),
                'closed_at': position.closed_at.isoformat()
            }
            
            # Add signal data if available
            if signal:
                position_data.update({
                    'currency_pair': signal.currency_pair,
                    'signal_type': signal.signal_type,
                    'leverage': signal.leverage
                })
            else:
                # Provide default values if signal is missing
                position_data.update({
                    'currency_pair': 'Unknown',
                    'signal_type': 'unknown',
                    'leverage': 1
                })
            
            positions_data.append(position_data)
        
        return jsonify({
            'success': True,
            'history': positions_data
        })
    except Exception as e:
        # Log the error for debugging
        print(f"Error fetching trade history: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error fetching trade history',
            'error': str(e)
        }), 500
    
@trade.route('/orders')
@login_required
def orders():
    """
    Get user's open orders.
    Returns a list of orders that haven't been filled or canceled.
    """
    try:
        # Get user's open orders
        open_orders = Order.query.filter_by(
            user_id=current_user.id,
            status='open'
        ).order_by(Order.created_at.desc()).all()
        
        orders_data = []
        for order in open_orders:
            # Get current market price for this pair
            current_price = get_current_price(order.currency_pair)
            
            orders_data.append({
                'id': order.id,
                'currency_pair': order.currency_pair,
                'order_type': order.order_type,
                'side': order.side,
                'price': order.price,
                'amount': order.amount,
                'filled_amount': order.filled_amount,
                'status': order.status,
                'created_at': order.created_at.isoformat(),
                'current_price': current_price,
                # Calculate how close we are to filling the order (as percentage)
                'fill_proximity': abs((current_price - order.price) / order.price * 100)
            })
        
        return jsonify({
            'success': True,
            'orders': orders_data
        })
    except Exception as e:
        # Log the error for debugging
        print(f"Error fetching orders: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error fetching orders',
            'error': str(e)
        }), 500

@trade.route('/place-order', methods=['POST'])
@login_required
def place_order():
    """
    Place a new limit or stop order.
    """
    try:
        # Get form data
        currency_pair = request.form.get('currency_pair')
        order_type = request.form.get('order_type')
        side = request.form.get('side')
        price = request.form.get('price')
        amount = request.form.get('amount')
        
        # Validate inputs
        if not all([currency_pair, order_type, side, price, amount]):
            return jsonify({
                'success': False,
                'message': 'All fields are required'
            }), 400
        
        try:
            price = float(price)
            amount = float(amount)
        except ValueError:
            return jsonify({
                'success': False,
                'message': 'Price and amount must be valid numbers'
            }), 400
        
        if price <= 0 or amount <= 0:
            return jsonify({
                'success': False,
                'message': 'Price and amount must be greater than zero'
            }), 400
        
        if order_type not in ['limit', 'stop', 'stop-limit']:
            return jsonify({
                'success': False,
                'message': 'Invalid order type'
            }), 400
        
        if side not in ['buy', 'sell']:
            return jsonify({
                'success': False,
                'message': 'Invalid side'
            }), 400
        
        # Check if user has enough balance (for buy orders)
        if side == 'buy':
            # Extract the quote currency (e.g., USDT from BTC/USDT)
            quote_currency = currency_pair.split('/')[1]
            
            # Total cost = price * amount
            total_cost = price * amount
            
            # Check user's wallet balance
            wallet = Wallet.query.filter_by(
                user_id=current_user.id,
                currency=quote_currency
            ).first()
            
            if not wallet or wallet.spot_balance < total_cost:
                return jsonify({
                    'success': False,
                    'message': f'Insufficient {quote_currency} balance'
                }), 400
            
            # Reserve the funds by subtracting from available balance
            wallet.spot_balance -= total_cost
        
        # For sell orders, check if user has the base currency
        if side == 'sell':
            # Extract the base currency (e.g., BTC from BTC/USDT)
            base_currency = currency_pair.split('/')[0]
            
            # Check user's wallet balance
            wallet = Wallet.query.filter_by(
                user_id=current_user.id,
                currency=base_currency
            ).first()
            
            if not wallet or wallet.spot_balance < amount:
                return jsonify({
                    'success': False,
                    'message': f'Insufficient {base_currency} balance'
                }), 400
            
            # Reserve the funds by subtracting from available balance
            wallet.spot_balance -= amount
        
        # Create the order
        order = Order(
            user_id=current_user.id,
            currency_pair=currency_pair,
            order_type=order_type,
            side=side,
            price=price,
            amount=amount
        )
        
        db.session.add(order)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{side.capitalize()} {order_type} order placed successfully',
            'order': {
                'id': order.id,
                'currency_pair': order.currency_pair,
                'order_type': order.order_type,
                'side': order.side,
                'price': order.price,
                'amount': order.amount,
                'status': order.status,
                'created_at': order.created_at.isoformat()
            }
        })
    
    except Exception as e:
        # Rollback in case of error
        db.session.rollback()
        print(f"Error placing order: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error placing order',
            'error': str(e)
        }), 500

@trade.route('/cancel-order', methods=['POST'])
@login_required
def cancel_order():
    """
    Cancel an open order.
    """
    try:
        order_id = request.form.get('order_id')
        
        if not order_id:
            return jsonify({
                'success': False,
                'message': 'Order ID is required'
            }), 400
        
        try:
            order_id = int(order_id)
        except ValueError:
            return jsonify({
                'success': False,
                'message': 'Invalid order ID'
            }), 400
        
        # Find the order
        order = Order.query.filter_by(
            id=order_id,
            user_id=current_user.id,
            status='open'
        ).first()
        
        if not order:
            return jsonify({
                'success': False,
                'message': 'Order not found or already filled/canceled'
            }), 404
        
        # Update order status
        order.status = 'canceled'
        order.updated_at = datetime.utcnow()
        
        # Return reserved funds to user's wallet
        if order.side == 'buy':
            # For buy orders, return the quote currency (e.g., USDT)
            quote_currency = order.currency_pair.split('/')[1]
            total_cost = order.price * (order.amount - order.filled_amount)
            
            wallet = Wallet.query.filter_by(
                user_id=current_user.id,
                currency=quote_currency
            ).first()
            
            if wallet:
                wallet.spot_balance += total_cost
        
        elif order.side == 'sell':
            # For sell orders, return the base currency (e.g., BTC)
            base_currency = order.currency_pair.split('/')[0]
            remaining_amount = order.amount - order.filled_amount
            
            wallet = Wallet.query.filter_by(
                user_id=current_user.id,
                currency=base_currency
            ).first()
            
            if wallet:
                wallet.spot_balance += remaining_amount
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Order canceled successfully'
        })
    
    except Exception as e:
        # Rollback in case of error
        db.session.rollback()
        print(f"Error canceling order: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error canceling order',
            'error': str(e)
        }), 500