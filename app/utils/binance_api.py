# Add this to app/utils/crypto_api.py or create a new file app/utils/binance_api.py

import requests
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)

# Base URL for Binance API
BINANCE_API_URL = 'https://api.binance.com/api/v3'

def get_binance_ticker_price(symbol_pair):
    """
    Get the current price for a trading pair from Binance.
    
    Args:
        symbol_pair: Symbol pair in Binance format (e.g., 'BTCUSDT')
    
    Returns:
        float: Current price or 0 if error
    """
    try:
        response = requests.get(f"{BINANCE_API_URL}/ticker/price", params={'symbol': symbol_pair})
        if response.status_code == 200:
            data = response.json()
            return float(data['price'])
        else:
            logger.error(f"Binance API error: {response.status_code} - {response.text}")
            return 0
    except Exception as e:
        logger.error(f"Error fetching Binance price: {str(e)}")
        return 0

def get_binance_exchange_rate(from_currency, to_currency):
    """
    Get exchange rate between two currencies from Binance.
    
    Args:
        from_currency: Source currency code (e.g., 'BTC')
        to_currency: Target currency code (e.g., 'USDT')
    
    Returns:
        float: Exchange rate or 0 if error
    """
    try:
        # Handle special case: same currency
        if from_currency == to_currency:
            return 1.0
            
        # Direct pair
        symbol = f"{from_currency}{to_currency}"
        direct_rate = get_binance_ticker_price(symbol)
        
        if direct_rate > 0:
            return direct_rate
            
        # Try reverse pair
        symbol_reverse = f"{to_currency}{from_currency}"
        reverse_rate = get_binance_ticker_price(symbol_reverse)
        
        if reverse_rate > 0:
            return 1 / reverse_rate
            
        # If no direct pair exists, calculate via USDT
        if from_currency != 'USDT' and to_currency != 'USDT':
            # Get rates via USDT
            from_to_usdt = get_binance_ticker_price(f"{from_currency}USDT")
            to_to_usdt = get_binance_ticker_price(f"{to_currency}USDT")
            
            if from_to_usdt > 0 and to_to_usdt > 0:
                # Cross rate calculation
                return from_to_usdt / to_to_usdt
        
        logger.warning(f"Could not find valid exchange rate for {from_currency}/{to_currency}")
        return 0
    except Exception as e:
        logger.error(f"Error calculating exchange rate: {str(e)}")
        return 0

def get_all_binance_tickers():
    """
    Get all available ticker prices from Binance.
    
    Returns:
        dict: Dictionary mapping symbol pairs to their prices
    """
    try:
        response = requests.get(f"{BINANCE_API_URL}/ticker/price")
        if response.status_code == 200:
            data = response.json()
            return {item['symbol']: float(item['price']) for item in data}
        else:
            logger.error(f"Binance API error: {response.status_code} - {response.text}")
            return {}
    except Exception as e:
        logger.error(f"Error fetching all Binance tickers: {str(e)}")
        return {}

def get_binance_exchange_rates(base_currency, quote_currencies):
    """
    Get exchange rates for multiple currencies.
    Compatible interface with the existing get_exchange_rates function.
    
    Args:
        base_currency: Base currency code (e.g., 'USDT')
        quote_currencies: List of quote currency codes (e.g., ['BTC', 'ETH'])
    
    Returns:
        dict: Dictionary mapping currency codes to exchange rates
    """
    result = {}
    
    for quote_currency in quote_currencies:
        rate = get_binance_exchange_rate(base_currency, quote_currency)
        if rate > 0:
            result[quote_currency] = rate
    
    return result

# Cache for ticker data to avoid excessive API calls
_ticker_cache = {}
_last_cache_update = 0  # timestamp

def get_cached_binance_rates(max_age_seconds=60):
    """
    Get or update the cached ticker data.
    
    Args:
        max_age_seconds: Maximum age of cache in seconds
    
    Returns:
        dict: Dictionary of ticker data
    """
    global _ticker_cache, _last_cache_update
    
    import time
    current_time = time.time()
    
    # Update cache if it's empty or too old
    if not _ticker_cache or (current_time - _last_cache_update) > max_age_seconds:
        _ticker_cache = get_all_binance_tickers()
        _last_cache_update = current_time
        
    return _ticker_cache