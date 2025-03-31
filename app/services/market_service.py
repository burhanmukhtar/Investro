# app/services/market_service.py
import logging
from app.utils.crypto_api import (
    get_market_overview, get_coin_details, get_chart_data, 
    get_current_price, get_popular_coins, get_new_listings
)

logger = logging.getLogger(__name__)

def get_market_data(limit=100, offset=0):
    """
    Get market data.
    
    Args:
        limit: Number of coins to return
        offset: Offset for pagination
    
    Returns:
        List of cryptocurrency market data
    """
    try:
        return get_market_overview(limit, offset)
    except Exception as e:
        logger.error(f"Error in get_market_data: {str(e)}")
        # Return empty list in case of error
        return []

def get_coin_data(symbol):
    """
    Get detailed data for a specific coin.
    
    Args:
        symbol: Cryptocurrency symbol (e.g., 'BTC')
    
    Returns:
        Dictionary with coin details
    """
    try:
        return get_coin_details(symbol)
    except Exception as e:
        logger.error(f"Error in get_coin_data: {str(e)}")
        # Return empty dict in case of error
        return {}

def get_chart_data_service(symbol, interval='1d', limit=100):
    """
    Get historical chart data for a cryptocurrency.
    
    Args:
        symbol: Cryptocurrency symbol (e.g., 'BTC')
        interval: Time interval
        limit: Number of data points to return
    
    Returns:
        List of OHLCV data points
    """
    try:
        return get_chart_data(symbol, interval, limit)
    except Exception as e:
        logger.error(f"Error in get_chart_data_service: {str(e)}")
        # Return empty list in case of error
        return []

def get_current_price_service(currency_pair):
    """
    Get current price for a trading pair.
    
    Args:
        currency_pair: Trading pair (e.g., 'BTC/USDT')
    
    Returns:
        Current price as a float or 0 if error
    """
    try:
        return get_current_price(currency_pair)
    except Exception as e:
        logger.error(f"Error in get_current_price_service: {str(e)}")
        # Return 0 in case of error
        return 0

def get_popular_coins_service(limit=10):
    """
    Get a list of popular coins.
    
    Args:
        limit: Number of coins to return
    
    Returns:
        List of popular cryptocurrency details
    """
    try:
        return get_popular_coins(limit)
    except Exception as e:
        logger.error(f"Error in get_popular_coins_service: {str(e)}")
        # Return empty list in case of error
        return []

def get_new_listings_service(limit=10):
    """
    Get a list of new cryptocurrency listings.
    
    Args:
        limit: Number of new listings to return
    
    Returns:
        List of new cryptocurrency listings
    """
    try:
        return get_new_listings(limit)
    except Exception as e:
        logger.error(f"Error in get_new_listings_service: {str(e)}")
        # Return empty list in case of error
        return []
    
def get_top_gainers_service(limit=20):
    """
    Get top gaining cryptocurrencies.
    
    Args:
        limit: Number of coins to return
    
    Returns:
        List of top gaining cryptocurrencies
    """
    try:
        from app.utils.crypto_api import get_top_gainers
        return get_top_gainers(limit)
    except Exception as e:
        logger.error(f"Error in get_top_gainers_service: {str(e)}")
        return []

def get_top_losers_service(limit=20):
    """
    Get top losing cryptocurrencies.
    
    Args:
        limit: Number of coins to return
    
    Returns:
        List of top losing cryptocurrencies
    """
    try:
        from app.utils.crypto_api import get_top_losers
        return get_top_losers(limit)
    except Exception as e:
        logger.error(f"Error in get_top_losers_service: {str(e)}")
        return []

def get_top_volume_service(limit=20):
    """
    Get cryptocurrencies with highest trading volume.
    
    Args:
        limit: Number of coins to return
    
    Returns:
        List of cryptocurrencies with highest trading volume
    """
    try:
        from app.utils.crypto_api import get_top_volume
        return get_top_volume(limit)
    except Exception as e:
        logger.error(f"Error in get_top_volume_service: {str(e)}")
        return []