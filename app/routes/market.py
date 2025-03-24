# app/routes/market.py
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app.services.market_service import (
    get_market_data, get_coin_data, get_chart_data_service,
    get_top_gainers_service, get_top_losers_service, get_top_volume_service
)
import logging

# Setup logger
logger = logging.getLogger(__name__)

market = Blueprint('market', __name__)

@market.route('/data')
@login_required
def market_data():
    """Get market data for cryptocurrency listings"""
    try:
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Get market data from service layer
        data = get_market_data(limit=limit, offset=offset)
        
        # Ensure we always return an array, even if there's an error
        if not isinstance(data, list):
            data = []
            
        # Return data directly without wrapping it in a success object
        # This maintains compatibility with frontend code expecting an array
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error fetching market data: {str(e)}")
        # Return empty array instead of error object to maintain compatibility
        return jsonify([])

@market.route('/coin/<symbol>')
@login_required
def coin_data(symbol):
    """Get detailed data for a specific coin"""
    try:
        # Normalize the symbol (uppercase for consistency)
        symbol = symbol.upper()
        
        # Get detailed data for a specific coin
        data = get_coin_data(symbol)
        
        if not data:
            logger.warning(f"Coin data not found for symbol: {symbol}")
            return jsonify({
                'success': False,
                'message': f'Coin {symbol} not found'
            }), 404
        
        # Ensure critical fields are present
        if 'symbol' not in data:
            data['symbol'] = symbol
            
        if 'name' not in data or not data['name']:
            data['name'] = symbol
            
        # Ensure numeric fields have default values if missing
        for field in ['current_price', 'market_cap', 'total_volume', 'price_change_percentage_24h']:
            if field not in data or data[field] is None:
                data[field] = 0
        
        return jsonify({
            'success': True,
            'data': data
        })
    except Exception as e:
        logger.error(f"Error fetching coin data for {symbol}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error fetching data for {symbol}: {str(e)}"
        }), 500

@market.route('/chart/<symbol>')
@login_required
def chart_data(symbol):
    """Get chart data for a specific coin"""
    try:
        interval = request.args.get('interval', '1d')  # 1d, 7d, 14d, 30d, 90d, 180d, 365d, max
        limit = request.args.get('limit', 100, type=int)
        
        # Get chart data for a specific coin
        data = get_chart_data_service(symbol, interval, limit)
        
        # For backward compatibility, return the data directly if it's already in the expected format
        if isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
            return jsonify(data)
            
        # Otherwise wrap it in a success response
        return jsonify({
            'success': True,
            'data': data
        })
    except Exception as e:
        logger.error(f"Error fetching chart data: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@market.route('/gainers')
@login_required
def top_gainers():
    """Get top gaining cryptocurrencies"""
    try:
        limit = request.args.get('limit', 20, type=int)
        data = get_top_gainers_service(limit)
        
        return jsonify({
            'success': True,
            'data': data
        })
    except Exception as e:
        logger.error(f"Error fetching top gainers: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@market.route('/losers')
@login_required
def top_losers():
    """Get top losing cryptocurrencies"""
    try:
        limit = request.args.get('limit', 20, type=int)
        data = get_top_losers_service(limit)
        
        return jsonify({
            'success': True,
            'data': data
        })
    except Exception as e:
        logger.error(f"Error fetching top losers: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@market.route('/volume')
@login_required
def top_volume():
    """Get cryptocurrencies with highest trading volume"""
    try:
        limit = request.args.get('limit', 20, type=int)
        data = get_top_volume_service(limit)
        
        return jsonify({
            'success': True,
            'data': data
        })
    except Exception as e:
        logger.error(f"Error fetching top volume: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500