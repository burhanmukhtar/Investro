# app/routes/market.py
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app.services.market_service import get_market_data, get_coin_data, get_chart_data

market = Blueprint('market', __name__)

@market.route('/data')
@login_required
def market_data():
    limit = request.args.get('limit', 100, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    # Get market data from API
    data = get_market_data(limit=limit, offset=offset)
    
    return jsonify(data)

@market.route('/coin/<symbol>')
@login_required
def coin_data(symbol):
    # Get detailed data for a specific coin
    data = get_coin_data(symbol)
    
    return jsonify(data)

@market.route('/chart/<symbol>')
@login_required
def chart_data(symbol):
    interval = request.args.get('interval', '1d')  # 1m, 5m, 15m, 1h, 4h, 1d, 1w
    limit = request.args.get('limit', 100, type=int)
    
    # Get chart data for a specific coin
    data = get_chart_data(symbol, interval, limit)
    
    return jsonify(data)

# app/routes/trade.py
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
from app.models.trade_signal import TradeSignal, TradePosition
from app.models.wallet import Wallet
from app.services.market_service import get_current_price
from datetime import datetime

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
    # Get user's closed positions
    closed_positions = TradePosition.query.filter_by(user_id=current_user.id, status='closed').order_by(TradePosition.closed_at.desc()).all()
    
    positions_data = []
    for position in closed_positions:
        signal = TradeSignal.query.get(position.signal_id)
        
        positions_data.append({
            'id': position.id,
            'signal_id': position.signal_id,
            'currency_pair': signal.currency_pair,
            'signal_type': signal.signal_type,
            'amount': position.amount,
            'entry_price': position.entry_price,
            'close_price': position.close_price,
            'profit_loss': position.profit_loss,
            'profit_loss_percentage': position.profit_loss_percentage,
            'leverage': signal.leverage,
            'created_at': position.created_at.isoformat(),
            'closed_at': position.closed_at.isoformat()
        })
    
    return jsonify({
        'success': True,
        'history': positions_data
    })