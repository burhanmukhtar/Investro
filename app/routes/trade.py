# app/routes/trade.py
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
from app.models.trade_signal import TradeSignal, TradePosition
from app.models.wallet import Wallet
from app.models.order import Order
from app.services.market_service import get_current_price_service as get_current_price
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
trade = Blueprint('trade', __name__)

@trade.route('/signals', methods=['GET'])
@login_required
def signals():
    """
    Get active trade signals.
    Returns JSON data for frontend.
    """
    try:
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
    except Exception as e:
        logger.error(f"Error fetching trade signals: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error fetching trade signals: {str(e)}"
        }), 500

@trade.route('/follow-signal', methods=['POST'])
@login_required
def follow_signal():
    """
    Follow a trade signal by creating a position.
    """
    try:
        signal_id = request.form.get('signal_id')
        amount = request.form.get('amount')
        
        # Validate input
        if not signal_id or not amount:
            return jsonify({'success': False, 'message': 'Signal ID and amount are required.'})
        
        try:
            signal_id = int(signal_id)
            amount = float(amount)
            if amount <= 0:
                return jsonify({'success': False, 'message': 'Amount must be greater than 0.'})
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
        try:
            current_price = get_current_price(signal.currency_pair)
        except Exception as e:
            logger.error(f"Error getting current price: {str(e)}")
            return jsonify({'success': False, 'message': f'Error getting current price: {str(e)}'})
            
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
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error following signal: {str(e)}")
        return jsonify({'success': False, 'message': f'Error following signal: {str(e)}'}), 500

@trade.route('/positions', methods=['GET'])
@login_required
def positions():
    try:
        # Get user's open positions
        open_positions = TradePosition.query.filter_by(user_id=current_user.id, status='open').all()
        
        positions_data = []
        for position in open_positions:
            # Get signal data, handle case where signal could be deleted
            signal = TradeSignal.query.get(position.signal_id)
            if not signal:
                continue
            
            try:
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
            except Exception as e:
                logger.error(f"Error calculating position data: {str(e)}")
                # Include position with error message
                positions_data.append({
                    'id': position.id,
                    'signal_id': position.signal_id,
                    'currency_pair': signal.currency_pair,
                    'signal_type': signal.signal_type,
                    'amount': position.amount,
                    'entry_price': position.entry_price,
                    'error': f"Could not calculate current values: {str(e)}"
                })
        
        return jsonify({
            'success': True,
            'positions': positions_data
        })
    except Exception as e:
        logger.error(f"Error fetching positions: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error fetching positions: {str(e)}"
        }), 500

@trade.route('/close-position', methods=['POST'])
@login_required
def close_position():
    """
    Close an open trading position.
    """
    try:
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

        # Get signal
        signal = TradeSignal.query.get(position.signal_id)
        if not signal:
            return jsonify({'success': False, 'message': 'Signal not found.'})
        
        # Extract base currency from pair (e.g., BTC from BTC/USDT)
        base_currency = signal.currency_pair.split('/')[1]
        
        try:
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
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error closing position: {str(e)}")
            return jsonify({'success': False, 'message': f'Error closing position: {str(e)}'}), 500
    except Exception as e:
        logger.error(f"Error processing position closure: {str(e)}")
        return jsonify({'success': False, 'message': f'Error processing position closure: {str(e)}'}), 500

@trade.route('/history', methods=['GET'])
@login_required
def history():
    """
    Get user's closed positions history.
    Returns JSON data for the frontend to display.
    """
    try:
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # Get user's closed positions with pagination
        pagination = TradePosition.query.filter_by(
            user_id=current_user.id, 
            status='closed'
        ).order_by(TradePosition.closed_at.desc()).paginate(page=page, per_page=per_page)
        
        # Get total number of positions
        total_positions = pagination.total
        total_pages = pagination.pages
        
        # Get positions for current page
        closed_positions = pagination.items
        
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
            'history': positions_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total_items': total_positions,
                'total_pages': total_pages
            }
        })
    except Exception as e:
        # Log the error
        logger.error(f"Error fetching trade history: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error fetching trade history',
            'error': str(e)
        }), 500

@trade.route('/orders', methods=['GET'])
@login_required
def orders():
    """
    Get user's open orders.
    Returns a list of orders that haven't been filled or canceled.
    """
    try:
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # Get user's open orders with pagination
        pagination = Order.query.filter_by(
            user_id=current_user.id,
            status='open'
        ).order_by(Order.created_at.desc()).paginate(page=page, per_page=per_page)
        
        # Get total number of orders
        total_orders = pagination.total
        total_pages = pagination.pages
        
        # Get orders for current page
        open_orders = pagination.items
        
        orders_data = []
        for order in open_orders:
            try:
                # Get current market price for this pair
                current_price = get_current_price(order.currency_pair)
                
                # Calculate fill proximity only if we have valid prices
                if current_price > 0 and order.price > 0:
                    fill_proximity = abs((current_price - order.price) / order.price * 100)
                else:
                    fill_proximity = None
                
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
                    'fill_proximity': fill_proximity
                })
            except Exception as e:
                # Add order with error information
                logger.error(f"Error getting price for order {order.id}: {str(e)}")
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
                    'error': f"Could not fetch current price: {str(e)}"
                })
        
        return jsonify({
            'success': True,
            'orders': orders_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total_items': total_orders,
                'total_pages': total_pages
            }
        })
    except Exception as e:
        # Log the error
        logger.error(f"Error fetching orders: {str(e)}")
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
        logger.error(f"Error placing order: {str(e)}")
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
        logger.error(f"Error canceling order: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error canceling order',
            'error': str(e)
        }), 500