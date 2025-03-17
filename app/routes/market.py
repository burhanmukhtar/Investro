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

