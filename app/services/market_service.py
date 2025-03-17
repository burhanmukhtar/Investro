# app/services/market_service.py
import requests
import json
import time
import random
import logging
from datetime import datetime, timedelta
from app.config import Config

logger = logging.getLogger(__name__)

def _get_coin_id(symbol):
    """
    Map cryptocurrency symbol to CoinGecko ID.
    """
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

def get_market_data(limit=100, offset=0):
    """
    Get market data from CoinGecko API.
    
    Args:
        limit: Number of coins to return
        offset: Offset for pagination
    
    Returns:
        List of cryptocurrency market data
    """
    try:
        # Fetch market data from CoinGecko
        response = requests.get(
            'https://api.coingecko.com/api/v3/coins/markets',
            params={
                'vs_currency': 'usd',
                'order': 'market_cap_desc',
                'per_page': limit,
                'page': offset // limit + 1,
                'sparkline': False
            },
            timeout=10  # 10-second timeout
        )
        
        response.raise_for_status()  # Raise an error for bad responses
        
        # Process the response
        data = response.json()
        
        # Transform data to match expected format
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
    except requests.RequestException as e:
        logger.error(f"Error fetching market data from CoinGecko: {e}")
        raise RuntimeError("Unable to fetch market data. Please try again later.") from e

def get_coin_data(symbol):
    """
    Get detailed data for a specific coin from CoinGecko.
    
    Args:
        symbol: Cryptocurrency symbol (e.g., 'BTC')
    
    Returns:
        Dictionary with coin details
    """
    try:
        # Get coin ID from symbol
        coin_id = _get_coin_id(symbol)
        
        # Fetch detailed coin data from CoinGecko
        response = requests.get(
            f'https://api.coingecko.com/api/v3/coins/{coin_id}',
            params={
                'localization': 'false',
                'tickers': 'false',
                'market_data': 'true',
                'community_data': 'false',
                'developer_data': 'false'
            },
            timeout=10
        )
        
        response.raise_for_status()
        
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
    except requests.RequestException as e:
        logger.error(f"Error fetching coin data from CoinGecko: {e}")
        raise RuntimeError(f"Unable to fetch data for {symbol}. Please try again later.") from e

def get_chart_data(symbol, interval='1d', limit=100):
    """
    Get historical chart data for a cryptocurrency from CoinGecko.
    
    Args:
        symbol: Cryptocurrency symbol (e.g., 'BTC')
        interval: Time interval
        limit: Number of data points to return
    
    Returns:
        List of OHLCV data points
    """
    try:
        # Get coin ID from symbol
        coin_id = _get_coin_id(symbol)
        
        # Map interval to CoinGecko's requirements
        days = limit if interval == '1d' else limit // 7
        
        # Fetch chart data from CoinGecko
        response = requests.get(
            f'https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart',
            params={
                'vs_currency': 'usd',
                'days': days,
                'interval': 'daily'
            },
            timeout=10
        )
        
        response.raise_for_status()
        
        # Process the response
        data = response.json()
        
        # Transform data to OHLCV-like structure
        result = []
        for item in data['prices']:
            timestamp = item[0]  # Timestamp in milliseconds
            price = item[1]  # Closing price
            
            result.append([
                timestamp,  # timestamp
                price,      # open
                price,      # high
                price,      # low
                price,      # close
                0           # volume (not provided by this endpoint)
            ])
        
        return result[:limit]
    except requests.RequestException as e:
        logger.error(f"Error fetching chart data from CoinGecko: {e}")
        raise RuntimeError(f"Unable to fetch chart data for {symbol}. Please try again later.") from e

def get_popular_coins(limit=5):
    """
    Get a list of popular coins from CoinGecko.
    
    Args:
        limit: Number of coins to return
    
    Returns:
        List of popular cryptocurrency details
    """
    try:
        # Fetch market data from CoinGecko
        response = requests.get(
            'https://api.coingecko.com/api/v3/coins/markets',
            params={
                'vs_currency': 'usd',
                'order': 'market_cap_desc',
                'per_page': limit,
                'page': 1,
                'sparkline': False
            },
            timeout=10
        )
        
        response.raise_for_status()
        
        coins = response.json()
        
        # Transform data to match expected format
        return [{
            'symbol': coin['symbol'].upper(),
            'name': coin['name'],
            'price': coin['current_price'],
            'change_24h': coin['price_change_percentage_24h']
        } for coin in coins]
    except requests.RequestException as e:
        logger.error(f"Error fetching popular coins from CoinGecko: {e}")
        raise RuntimeError("Unable to fetch popular coins. Please try again later.") from e

def get_new_listings(limit=5):
    """
    Get a list of new cryptocurrency listings from CoinGecko.
    
    Args:
        limit: Number of new listings to return
    
    Returns:
        List of new cryptocurrency listings
    """
    try:
        # Fetch new listings from CoinGecko
        response = requests.get(
            'https://api.coingecko.com/api/v3/coins/markets',
            params={
                'vs_currency': 'usd',
                'order': 'date_added_desc',
                'per_page': limit,
                'page': 1,
                'sparkline': False
            },
            timeout=10
        )
        
        response.raise_for_status()
        
        coins = response.json()
        
        # Transform data to match expected format
        return [{
            'symbol': coin['symbol'].upper(),
            'name': coin['name'],
            'price': coin['current_price'],
            'change_24h': coin['price_change_percentage_24h']
        } for coin in coins]
    except requests.RequestException as e:
        logger.error(f"Error fetching new listings from CoinGecko: {e}")
        raise RuntimeError("Unable to fetch new listings. Please try again later.") from e

def get_current_price(currency_pair):
    """
    Get current price for a trading pair from Binance.
    
    Args:
        currency_pair: Trading pair (e.g., 'BTC/USDT')
    
    Returns:
        Current price as a float
    """
    try:
        # Convert pair format from BTC/USDT to BTCUSDT
        binance_symbol = currency_pair.replace('/', '')
        
        response = requests.get(
            'https://api.binance.com/api/v3/ticker/price',
            params={'symbol': binance_symbol},
            timeout=10
        )
        
        response.raise_for_status()
        
        data = response.json()
        
        return float(data['price'])
    except requests.RequestException as e:
        logger.error(f"Error fetching current price from Binance: {e}")
        raise RuntimeError(f"Unable to fetch price for {currency_pair}. Please try again later.") from e