# app/services/market_service.py
import requests
import json
import time
import random
from datetime import datetime, timedelta
from app.config import Config

def get_market_data(limit=100, offset=0):
    """
    Get market data from a cryptocurrency API.
    
    This is a placeholder function. In a real implementation, you would integrate
    with a cryptocurrency API like CoinMarketCap, CoinGecko, or Binance API.
    
    For development, this returns mock data.
    """
    try:
        # Example for integrating with CoinGecko API
        # response = requests.get(
        #     'https://api.coingecko.com/api/v3/coins/markets',
        #     params={
        #         'vs_currency': 'usd',
        #         'order': 'market_cap_desc',
        #         'per_page': limit,
        #         'page': offset // limit + 1,
        #         'sparkline': False
        #     }
        # )
        # return response.json()
        
        # For development, return mock data
        mock_data = []
        for i in range(limit):
            idx = offset + i
            price = random.uniform(0.1, 60000)
            change_24h = random.uniform(-15, 15)
            volume_24h = price * random.uniform(1000, 1000000)
            market_cap = price * random.uniform(10000, 100000000)
            
            coin = {
                'id': f'coin_{idx}',
                'symbol': f'COIN{idx}',
                'name': f'Coin {idx}',
                'image': f'/static/images/coins/coin_{idx}.png',
                'current_price': price,
                'market_cap': market_cap,
                'market_cap_rank': idx + 1,
                'total_volume': volume_24h,
                'price_change_percentage_24h': change_24h,
                'circulating_supply': random.uniform(1000, 100000000),
                'total_supply': random.uniform(1000, 100000000),
                'max_supply': random.uniform(1000, 100000000),
                'last_updated': datetime.utcnow().isoformat()
            }
            mock_data.append(coin)
        
        return mock_data
    except Exception as e:
        print(f"Error fetching market data: {e}")
        return []

def get_coin_data(symbol):
    """
    Get detailed data for a specific coin.
    
    This is a placeholder function. In a real implementation, you would integrate
    with a cryptocurrency API.
    
    For development, this returns mock data.
    """
    try:
        # For development, return mock data
        price = random.uniform(0.1, 60000)
        change_24h = random.uniform(-15, 15)
        volume_24h = price * random.uniform(1000, 1000000)
        market_cap = price * random.uniform(10000, 100000000)
        
        return {
            'id': f'coin_{symbol}',
            'symbol': symbol,
            'name': f'Coin {symbol}',
            'description': f'This is a detailed description for {symbol} coin.',
            'image': f'/static/images/coins/{symbol}.png',
            'current_price': price,
            'market_cap': market_cap,
            'market_cap_rank': random.randint(1, 100),
            'total_volume': volume_24h,
            'price_change_percentage_24h': change_24h,
            'price_change_percentage_7d': random.uniform(-30, 30),
            'price_change_percentage_30d': random.uniform(-50, 50),
            'circulating_supply': random.uniform(1000, 100000000),
            'total_supply': random.uniform(1000, 100000000),
            'max_supply': random.uniform(1000, 100000000),
            'ath': price * random.uniform(1, 5),
            'ath_date': (datetime.utcnow() - timedelta(days=random.randint(1, 365))).isoformat(),
            'atl': price * random.uniform(0.1, 0.9),
            'atl_date': (datetime.utcnow() - timedelta(days=random.randint(366, 1000))).isoformat(),
            'last_updated': datetime.utcnow().isoformat()
        }
    except Exception as e:
        print(f"Error fetching coin data: {e}")
        return {}

def get_chart_data(symbol, interval='1d', limit=100):
    """
    Get chart data for a specific coin.
    
    This is a placeholder function. In a real implementation, you would integrate
    with a cryptocurrency API.
    
    For development, this returns mock data.
    """
    try:
        # For development, return mock data
        mock_data = []
        base_price = random.uniform(0.1, 60000)
        
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
            
            # Generate OHLC (Open, High, Low, Close) values
            price_change = base_price * random.uniform(-0.1, 0.1)
            open_price = base_price
            close_price = base_price + price_change
            high_price = max(open_price, close_price) * random.uniform(1, 1.05)
            low_price = min(open_price, close_price) * random.uniform(0.95, 1)
            volume = base_price * random.uniform(1000, 100000)
            
            # Update base price for next iteration
            base_price = close_price
            
            # Candlestick data format: [timestamp, open, high, low, close, volume]
            candlestick = [timestamp, open_price, high_price, low_price, close_price, volume]
            mock_data.append(candlestick)
        
        return mock_data
    except Exception as e:
        print(f"Error fetching chart data: {e}")
        return []

def get_popular_coins(limit=5):
    """
    Get a list of popular coins.
    
    This is a placeholder function. In a real implementation, you would integrate
    with a cryptocurrency API.
    
    For development, this returns mock data.
    """
    try:
        # For development, return mock data for popular coins
        popular_coins = [
            {'symbol': 'BTC', 'name': 'Bitcoin', 'price': random.uniform(20000, 60000), 'change_24h': random.uniform(-5, 5)},
            {'symbol': 'ETH', 'name': 'Ethereum', 'price': random.uniform(1000, 3000), 'change_24h': random.uniform(-5, 5)},
            {'symbol': 'BNB', 'name': 'Binance Coin', 'price': random.uniform(200, 500), 'change_24h': random.uniform(-5, 5)},
            {'symbol': 'XRP', 'name': 'Ripple', 'price': random.uniform(0.1, 1), 'change_24h': random.uniform(-5, 5)},
            {'symbol': 'ADA', 'name': 'Cardano', 'price': random.uniform(0.1, 2), 'change_24h': random.uniform(-5, 5)}
        ]
        
        return popular_coins[:limit]
    except Exception as e:
        print(f"Error fetching popular coins: {e}")
        return []

def get_new_listings(limit=5):
    """
    Get a list of newly listed coins.
    
    This is a placeholder function. In a real implementation, you would integrate
    with a cryptocurrency API.
    
    For development, this returns mock data.
    """
    try:
        # For development, return mock data for new listings
        new_listings = [
            {'symbol': 'NEW1', 'name': 'New Coin 1', 'price': random.uniform(0.01, 1), 'change_24h': random.uniform(10, 100)},
            {'symbol': 'NEW2', 'name': 'New Coin 2', 'price': random.uniform(0.01, 1), 'change_24h': random.uniform(10, 100)},
            {'symbol': 'NEW3', 'name': 'New Coin 3', 'price': random.uniform(0.01, 1), 'change_24h': random.uniform(10, 100)},
            {'symbol': 'NEW4', 'name': 'New Coin 4', 'price': random.uniform(0.01, 1), 'change_24h': random.uniform(10, 100)},
            {'symbol': 'NEW5', 'name': 'New Coin 5', 'price': random.uniform(0.01, 1), 'change_24h': random.uniform(10, 100)}
        ]
        
        return new_listings[:limit]
    except Exception as e:
        print(f"Error fetching new listings: {e}")
        return []

def get_current_price(currency_pair):
    """
    Get current price for a currency pair.
    
    This is a placeholder function. In a real implementation, you would integrate
    with a cryptocurrency API.
    
    For development, this returns a random price.
    """
    try:
        # For development, return a random price
        if currency_pair == 'BTC/USDT':
            return random.uniform(20000, 60000)
        elif currency_pair == 'ETH/USDT':
            return random.uniform(1000, 3000)
        elif currency_pair == 'BNB/USDT':
            return random.uniform(200, 500)
        elif currency_pair == 'XRP/USDT':
            return random.uniform(0.1, 1)
        else:
            return random.uniform(0.1, 1000)
    except Exception as e:
        print(f"Error fetching current price: {e}")
        return 0