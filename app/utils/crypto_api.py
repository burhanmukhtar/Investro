# app/utils/crypto_api.py
"""
Cryptocurrency API integration.
Functions for fetching market data, prices, and other cryptocurrency information.
"""
import json
import time
import random
import requests
import logging
from datetime import datetime, timedelta
from app.config import Config

logger = logging.getLogger(__name__)

def get_exchange_rates(base_currency='USDT', quote_currencies=None):
    """
    Get exchange rates for the specified currencies.
    
    In a real implementation, this would fetch data from a cryptocurrency
    API like CoinGecko, CoinMarketCap, or Binance.
    
    Args:
        base_currency: Base currency for rates
        quote_currencies: List of quote currencies to get rates for
    
    Returns:
        Dictionary of exchange rates
    """
    try:
        # If in development mode, return mock data
        if Config.ENVIRONMENT == 'development':
            return _get_mock_exchange_rates(base_currency, quote_currencies)
        
        # In production, use a real API
        # Example with CoinGecko
        if base_currency == 'USDT':
            # For USDT as base, we need to get rates as 1/rate
            response = requests.get(
                'https://api.coingecko.com/api/v3/simple/price',
                params={
                    'ids': 'bitcoin,ethereum,binancecoin,ripple',
                    'vs_currencies': 'usd'
                }
            )
            
            data = response.json()
            
            # Convert the data to our format
            rates = {
                'BTC': 1 / data['bitcoin']['usd'],
                'ETH': 1 / data['ethereum']['usd'],
                'BNB': 1 / data['binancecoin']['usd'],
                'XRP': 1 / data['ripple']['usd']
            }
        else:
            # For other base currencies, get their USD rate first
            base_id = _get_coin_id(base_currency)
            
            response = requests.get(
                'https://api.coingecko.com/api/v3/simple/price',
                params={
                    'ids': base_id,
                    'vs_currencies': 'usd'
                }
            )
            
            base_data = response.json()
            base_usd_rate = base_data[base_id]['usd']
            
            # Then get rates for quote currencies
            quote_ids = [_get_coin_id(c) for c in quote_currencies]
            
            response = requests.get(
                'https://api.coingecko.com/api/v3/simple/price',
                params={
                    'ids': ','.join(quote_ids),
                    'vs_currencies': 'usd'
                }
            )
            
            quote_data = response.json()
            
            # Calculate rates
            rates = {}
            for currency, coin_id in zip(quote_currencies, quote_ids):
                quote_usd_rate = quote_data[coin_id]['usd']
                rates[currency] = quote_usd_rate / base_usd_rate
        
        return rates
    except Exception as e:
        logger.error(f"Error fetching exchange rates: {str(e)}")
        # Fall back to mock data in case of error
        return _get_mock_exchange_rates(base_currency, quote_currencies)

def get_coin_details(symbol):
    """
    Get detailed information for a cryptocurrency.
    
    Args:
        symbol: Cryptocurrency symbol (e.g., 'BTC')
    
    Returns:
        Dictionary with coin details
    """
    try:
        # If in development mode, return mock data
        if Config.ENVIRONMENT == 'development':
            return _get_mock_coin_details(symbol)
        
        # In production, use a real API
        # Example with CoinGecko
        coin_id = _get_coin_id(symbol)
        
        response = requests.get(
            f'https://api.coingecko.com/api/v3/coins/{coin_id}',
            params={
                'localization': 'false',
                'tickers': 'false',
                'market_data': 'true',
                'community_data': 'false',
                'developer_data': 'false'
            }
        )
        
        data = response.json()
        
        # Extract relevant information
        return {
            'id': data['id'],
            'symbol': data['symbol'].upper(),
            'name': data['name'],
            'description': data.get('description', {}).get('en', ''),
            'image': data['image']['large'],
            'current_price': data['market_data']['current_price']['usd'],
            'market_cap': data['market_data']['market_cap']['usd'],
            'market_cap_rank': data['market_data']['market_cap_rank'],
            'total_volume': data['market_data']['total_volume']['usd'],
            'price_change_percentage_24h': data['market_data']['price_change_percentage_24h'],
            'price_change_percentage_7d': data['market_data']['price_change_percentage_7d'],
            'price_change_percentage_30d': data['market_data']['price_change_percentage_30d'],
            'circulating_supply': data['market_data']['circulating_supply'],
            'total_supply': data['market_data']['total_supply'],
            'max_supply': data['market_data']['max_supply'],
            'ath': data['market_data']['ath']['usd'],
            'ath_date': data['market_data']['ath_date']['usd'],
            'atl': data['market_data']['atl']['usd'],
            'atl_date': data['market_data']['atl_date']['usd'],
            'last_updated': data['last_updated']
        }
    except Exception as e:
        logger.error(f"Error fetching coin details: {str(e)}")
        # Fall back to mock data in case of error
        return _get_mock_coin_details(symbol)

def get_market_overview(limit=100, offset=0):
    """
    Get an overview of the cryptocurrency market.
    
    Args:
        limit: Number of coins to return
        offset: Offset for pagination
    
    Returns:
        List of dictionaries with market data
    """
    try:
        # If in development mode, return mock data
        if Config.ENVIRONMENT == 'development':
            return _get_mock_market_overview(limit, offset)
        
        # In production, use a real API
        # Example with CoinGecko
        response = requests.get(
            'https://api.coingecko.com/api/v3/coins/markets',
            params={
                'vs_currency': 'usd',
                'order': 'market_cap_desc',
                'per_page': limit,
                'page': offset // limit + 1,
                'sparkline': 'false'
            }
        )
        
        data = response.json()
        
        # Extract relevant information
        result = []
        for coin in data:
            result.append({
                'id': coin['id'],
                'symbol': coin['symbol'].upper(),
                'name': coin['name'],
                'image': coin['image'],
                'current_price': coin['current_price'],
                'market_cap': coin['market_cap'],
                'market_cap_rank': coin['market_cap_rank'],
                'total_volume': coin['total_volume'],
                'price_change_percentage_24h': coin['price_change_percentage_24h'],
                'circulating_supply': coin['circulating_supply'],
                'total_supply': coin['total_supply'],
                'max_supply': coin['max_supply'],
                'last_updated': coin['last_updated']
            })
        
        return result
    except Exception as e:
        logger.error(f"Error fetching market overview: {str(e)}")
        # Fall back to mock data in case of error
        return _get_mock_market_overview(limit, offset)

def get_chart_data(symbol, interval='1d', limit=100):
    """
    Get historical chart data for a cryptocurrency.
    
    Args:
        symbol: Cryptocurrency symbol (e.g., 'BTC')
        interval: Time interval ('1m', '5m', '15m', '1h', '4h', '1d', '1w')
        limit: Number of data points to return
    
    Returns:
        List of OHLCV data points
    """
    try:
        # If in development mode, return mock data
        if Config.ENVIRONMENT == 'development':
            return _get_mock_chart_data(symbol, interval, limit)
        
        # In production, use a real API
        # Example with Binance
        # Map our intervals to Binance intervals
        binance_intervals = {
            '1m': '1m',
            '5m': '5m',
            '15m': '15m',
            '1h': '1h',
            '4h': '4h',
            '1d': '1d',
            '1w': '1w'
        }
        
        binance_interval = binance_intervals.get(interval, '1d')
        
        # For Binance API, we need to use symbol pairs like BTCUSDT
        symbol_pair = f"{symbol.upper()}USDT"
        
        # app/utils/crypto_api.py (continued)
        response = requests.get(
            'https://api.binance.com/api/v3/klines',
            params={
                'symbol': symbol_pair,
                'interval': binance_interval,
                'limit': limit
            }
        )
        
        data = response.json()
        
        # Convert to our format
        # Binance kline format: [time, open, high, low, close, volume, ...]
        result = []
        for candle in data:
            result.append([
                candle[0],  # timestamp
                float(candle[1]),  # open
                float(candle[2]),  # high
                float(candle[3]),  # low
                float(candle[4]),  # close
                float(candle[5])   # volume
            ])
        
        return result
    except Exception as e:
        logger.error(f"Error fetching chart data: {str(e)}")
        # Fall back to mock data in case of error
        return _get_mock_chart_data(symbol, interval, limit)

def get_current_price(symbol_pair):
    """
    Get the current price for a trading pair.
    
    Args:
        symbol_pair: Trading pair (e.g., 'BTC/USDT')
    
    Returns:
        Current price as a float
    """
    try:
        # If in development mode, return mock data
        if Config.ENVIRONMENT == 'development':
            return _get_mock_current_price(symbol_pair)
        
        # In production, use a real API
        # Example with Binance
        # Convert pair format from BTC/USDT to BTCUSDT
        binance_symbol = symbol_pair.replace('/', '')
        
        response = requests.get(
            'https://api.binance.com/api/v3/ticker/price',
            params={
                'symbol': binance_symbol
            }
        )
        
        data = response.json()
        
        return float(data['price'])
    except Exception as e:
        logger.error(f"Error fetching current price: {str(e)}")
        # Fall back to mock data in case of error
        return _get_mock_current_price(symbol_pair)

# Helper functions for coin ID mapping
def _get_coin_id(symbol):
    """
    Map cryptocurrency symbol to CoinGecko ID.
    
    Args:
        symbol: Cryptocurrency symbol (e.g., 'BTC')
    
    Returns:
        CoinGecko coin ID
    """
    # Common mappings
    mappings = {
        'BTC': 'bitcoin',
        'ETH': 'ethereum',
        'BNB': 'binancecoin',
        'XRP': 'ripple',
        'USDT': 'tether',
        'USDC': 'usd-coin',
        'ADA': 'cardano',
        'DOGE': 'dogecoin',
        'SOL': 'solana'
    }
    
    return mappings.get(symbol.upper(), symbol.lower())

# Mock data functions for development
def _get_mock_exchange_rates(base_currency='USDT', quote_currencies=None):
    """
    Generate mock exchange rates for development.
    
    Args:
        base_currency: Base currency for rates
        quote_currencies: List of quote currencies to get rates for
    
    Returns:
        Dictionary of exchange rates
    """
    if quote_currencies is None:
        quote_currencies = ['BTC', 'ETH', 'BNB', 'XRP']
    
    # Filter out base currency if it's in quote_currencies
    quote_currencies = [c for c in quote_currencies if c != base_currency]
    
    # Mock rates for USDT as base
    usdt_rates = {
        'BTC': 0.000037,
        'ETH': 0.00048,
        'BNB': 0.0042,
        'XRP': 2.3,
        'ADA': 2.0,
        'DOGE': 12.5,
        'SOL': 0.012
    }
    
    # Mock rates for BTC as base
    btc_rates = {
        'USDT': 27000,
        'ETH': 13,
        'BNB': 113,
        'XRP': 62000,
        'ADA': 54000,
        'DOGE': 337500,
        'SOL': 324
    }
    
    # Mock rates for ETH as base
    eth_rates = {
        'USDT': 2080,
        'BTC': 0.077,
        'BNB': 8.7,
        'XRP': 4800,
        'ADA': 4160,
        'DOGE': 26000,
        'SOL': 25
    }
    
    # Choose the appropriate rate set based on base_currency
    if base_currency == 'USDT':
        base_rates = usdt_rates
    elif base_currency == 'BTC':
        base_rates = btc_rates
    elif base_currency == 'ETH':
        base_rates = eth_rates
    else:
        # For other base currencies, just return some random rates
        base_rates = {c: random.uniform(0.001, 100) for c in quote_currencies}
    
    # Filter to only requested quote currencies
    return {c: base_rates.get(c, random.uniform(0.001, 100)) for c in quote_currencies}

def _get_mock_coin_details(symbol):
    """
    Generate mock coin details for development.
    
    Args:
        symbol: Cryptocurrency symbol (e.g., 'BTC')
    
    Returns:
        Dictionary with mock coin details
    """
    # Base price for the coin
    if symbol == 'BTC':
        base_price = random.uniform(25000, 35000)
        name = 'Bitcoin'
        description = 'Bitcoin is a decentralized digital currency without a central bank or administrator.'
        market_cap = base_price * random.uniform(18000000, 19000000)
        circulating_supply = random.uniform(18500000, 19000000)
        total_supply = 21000000
        max_supply = 21000000
    elif symbol == 'ETH':
        base_price = random.uniform(1500, 2500)
        name = 'Ethereum'
        description = 'Ethereum is an open-source, blockchain-based platform that enables developers to build and deploy smart contracts.'
        market_cap = base_price * random.uniform(115000000, 120000000)
        circulating_supply = random.uniform(115000000, 120000000)
        total_supply = None
        max_supply = None
    elif symbol == 'BNB':
        base_price = random.uniform(200, 300)
        name = 'Binance Coin'
        description = 'Binance Coin is the cryptocurrency issued by the Binance exchange.'
        market_cap = base_price * random.uniform(150000000, 160000000)
        circulating_supply = random.uniform(150000000, 160000000)
        total_supply = 166801148
        max_supply = 166801148
    elif symbol == 'XRP':
        base_price = random.uniform(0.3, 0.6)
        name = 'XRP'
        description = 'XRP is the native cryptocurrency of the XRP Ledger, which is an open-source, permissionless and decentralized blockchain.'
        market_cap = base_price * random.uniform(45000000000, 50000000000)
        circulating_supply = random.uniform(45000000000, 50000000000)
        total_supply = 100000000000
        max_supply = 100000000000
    else:
        base_price = random.uniform(0.1, 1000)
        name = f'Coin {symbol}'
        description = f'This is a mock description for {symbol}.'
        market_cap = base_price * random.uniform(1000000, 1000000000)
        circulating_supply = random.uniform(1000000, 1000000000)
        total_supply = circulating_supply * random.uniform(1, 2)
        max_supply = total_supply
    
    # Generate price change percentages
    price_change_24h = random.uniform(-10, 10)
    price_change_7d = random.uniform(-20, 20)
    price_change_30d = random.uniform(-30, 30)
    
    # Generate all-time high and low
    ath = base_price * random.uniform(1.5, 3)
    atl = base_price * random.uniform(0.1, 0.5)
    
    # Generate dates
    now = datetime.utcnow()
    ath_date = (now - timedelta(days=random.randint(30, 1000))).isoformat()
    atl_date = (now - timedelta(days=random.randint(30, 1000))).isoformat()
    last_updated = now.isoformat()
    
    return {
        'id': f'coin_{symbol.lower()}',
        'symbol': symbol.upper(),
        'name': name,
        'description': description,
        'image': f'/static/images/coins/{symbol.lower()}.png',
        'current_price': base_price,
        'market_cap': market_cap,
        'market_cap_rank': random.randint(1, 100),
        'total_volume': market_cap * random.uniform(0.01, 0.1),
        'price_change_percentage_24h': price_change_24h,
        'price_change_percentage_7d': price_change_7d,
        'price_change_percentage_30d': price_change_30d,
        'circulating_supply': circulating_supply,
        'total_supply': total_supply,
        'max_supply': max_supply,
        'ath': ath,
        'ath_date': ath_date,
        'atl': atl,
        'atl_date': atl_date,
        'last_updated': last_updated
    }

def _get_mock_market_overview(limit=100, offset=0):
    """
    Generate mock market overview data for development.
    
    Args:
        limit: Number of coins to return
        offset: Offset for pagination
    
    Returns:
        List of dictionaries with mock market data
    """
    result = []
    
    # Generate data for popular coins first
    popular_coins = ['BTC', 'ETH', 'BNB', 'XRP', 'ADA', 'DOGE', 'SOL', 'DOT', 'AVAX', 'MATIC']
    
    for i, symbol in enumerate(popular_coins, start=1):
        if i > limit:
            break
        
        coin = _get_mock_coin_details(symbol)
        
        result.append({
            'id': coin['id'],
            'symbol': coin['symbol'],
            'name': coin['name'],
            'image': coin['image'],
            'current_price': coin['current_price'],
            'market_cap': coin['market_cap'],
            'market_cap_rank': i,
            'total_volume': coin['total_volume'],
            'price_change_percentage_24h': coin['price_change_percentage_24h'],
            'circulating_supply': coin['circulating_supply'],
            'total_supply': coin['total_supply'],
            'max_supply': coin['max_supply'],
            'last_updated': coin['last_updated']
        })
    
    # Generate data for additional coins
    for i in range(len(popular_coins) + 1, limit + 1):
        symbol = f'COIN{i + offset}'
        
        price = random.uniform(0.1, 1000)
        market_cap = price * random.uniform(1000000, 1000000000)
        
        result.append({
            'id': f'coin_{i + offset}',
            'symbol': symbol,
            'name': f'Coin {i + offset}',
            'image': f'/static/images/coins/default.png',
            'current_price': price,
            'market_cap': market_cap,
            'market_cap_rank': i + offset,
            'total_volume': market_cap * random.uniform(0.01, 0.1),
            'price_change_percentage_24h': random.uniform(-10, 10),
            'circulating_supply': random.uniform(1000000, 1000000000),
            'total_supply': random.uniform(1000000, 1000000000),
            'max_supply': random.uniform(1000000, 1000000000),
            'last_updated': datetime.utcnow().isoformat()
        })
    
    return result

def _get_mock_chart_data(symbol, interval='1d', limit=100):
    """
    Generate mock chart data for development.
    
    Args:
        symbol: Cryptocurrency symbol (e.g., 'BTC')
        interval: Time interval ('1m', '5m', '15m', '1h', '4h', '1d', '1w')
        limit: Number of data points to return
    
    Returns:
        List of mock OHLCV data points
    """
    result = []
    
    # Set base price based on symbol
    if symbol == 'BTC':
        base_price = random.uniform(25000, 35000)
    elif symbol == 'ETH':
        base_price = random.uniform(1500, 2500)
    elif symbol == 'BNB':
        base_price = random.uniform(200, 300)
    elif symbol == 'XRP':
        base_price = random.uniform(0.3, 0.6)
    else:
        base_price = random.uniform(0.1, 1000)
    
    # Generate timestamps
    now = int(time.time() * 1000)
    
    # Determine time interval in milliseconds
    if interval == '1m':
        interval_ms = 60 * 1000
    elif interval == '5m':
        interval_ms = 5 * 60 * 1000
    elif interval == '15m':
        interval_ms = 15 * 60 * 1000
    elif interval == '1h':
        interval_ms = 60 * 60 * 1000
    elif interval == '4h':
        interval_ms = 4 * 60 * 60 * 1000
    elif interval == '1d':
        interval_ms = 24 * 60 * 60 * 1000
    elif interval == '1w':
        interval_ms = 7 * 24 * 60 * 60 * 1000
    else:
        interval_ms = 24 * 60 * 60 * 1000  # Default to 1d
    
    # Generate candlestick data
    for i in range(limit):
        timestamp = now - ((limit - i) * interval_ms)
        
        # Generate OHLC (Open, High, Low, Close) values with some randomness
        price_change = base_price * random.uniform(-0.05, 0.05)
        open_price = base_price
        close_price = base_price + price_change
        high_price = max(open_price, close_price) * random.uniform(1, 1.02)
        low_price = min(open_price, close_price) * random.uniform(0.98, 1)
        volume = base_price * random.uniform(1000, 100000)
        
        # Update base price for next iteration
        base_price = close_price
        
        # Create a candlestick
        candle = [timestamp, open_price, high_price, low_price, close_price, volume]
        result.append(candle)
    
    return result

def _get_mock_current_price(symbol_pair):
    """
    Generate a mock current price for development.
    
    Args:
        symbol_pair: Trading pair (e.g., 'BTC/USDT')
    
    Returns:
        Mock current price as a float
    """
    # Extract base symbol
    base_symbol = symbol_pair.split('/')[0]
    
    # Set price based on symbol
    if base_symbol == 'BTC':
        return random.uniform(25000, 35000)
    elif base_symbol == 'ETH':
        return random.uniform(1500, 2500)
    elif base_symbol == 'BNB':
        return random.uniform(200, 300)
    elif base_symbol == 'XRP':
        return random.uniform(0.3, 0.6)
    else:
        return random.uniform(0.1, 1000)