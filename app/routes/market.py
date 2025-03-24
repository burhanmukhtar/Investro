# app/routes/market.py
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app.services.market_service import (
    get_market_data, get_coin_data, get_chart_data_service as get_chart_data,
    get_popular_coins_service as get_popular_coins,
    get_new_listings_service as get_new_listings
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
        # Get detailed data for a specific coin
        data = get_coin_data(symbol)
        
        if not data:
            return jsonify({
                'success': False,
                'message': f'Coin {symbol} not found'
            }), 404
        
        return jsonify({
            'success': True,
            'data': data
        })
    except Exception as e:
        logger.error(f"Error fetching coin data: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@market.route('/chart/<symbol>')
@login_required
def chart_data(symbol):
    """Get chart data for a specific coin"""
    try:
        interval = request.args.get('interval', '1d')  # 1d, 7d, 14d, 30d, 90d, 180d, 365d, max
        limit = request.args.get('limit', 100, type=int)
        
        # Get chart data for a specific coin
        data = get_chart_data(symbol, interval, limit)
        
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

@market.route('/popular')
@login_required
def popular_coins():
    """Get list of popular coins"""
    try:
        limit = request.args.get('limit', 5, type=int)
        
        # Get popular coins
        data = get_popular_coins(limit)
        
        return jsonify({
            'success': True,
            'data': data
        })
    except Exception as e:
        logger.error(f"Error fetching popular coins: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@market.route('/new-listings')
@login_required
def new_listings():
    """Get list of new coin listings"""
    try:
        limit = request.args.get('limit', 5, type=int)
        
        # Get new listings
        data = get_new_listings(limit)
        
        return jsonify({
            'success': True,
            'data': data
        })
    except Exception as e:
        logger.error(f"Error fetching new listings: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500