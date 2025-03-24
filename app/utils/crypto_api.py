# app/utils/crypto_api.py
"""
Cryptocurrency API integration.
Functions for fetching market data, prices, and other cryptocurrency information.
Using CoinGecko Pro API.
"""
import requests
import logging
import time
from datetime import datetime, timedelta
from app.config import Config

logger = logging.getLogger(__name__)

# Base URL for CoinGecko API
COINGECKO_API_URL = 'https://pro-api.coingecko.com/api/v3'

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

def get_exchange_rates(base_currency='USDT', quote_currencies=None):
    """
    Get exchange rates for the specified currencies.
    
    Args:
        base_currency: Base currency for rates
        quote_currencies: List of quote currencies to get rates for
    
    Returns:
        Dictionary of exchange rates
    """
    try:
        if quote_currencies is None:
            quote_currencies = ['BTC', 'ETH', 'BNB', 'XRP']
        
        # Filter out base currency if it's in quote_currencies
        quote_currencies = [c for c in quote_currencies if c != base_currency]
        
        # If base currency is USDT, we can use simpler approach
        if base_currency == 'USDT':
            # Get rates for each crypto against USD/USDT
            rates = {}
            for currency in quote_currencies:
                coin_id = _get_coin_id(currency)
                response = requests.get(
                    f'{COINGECKO_API_URL}/simple/price',
                    params={
                        'ids': coin_id,
                        'vs_currencies': 'usd',
                        'x_cg_pro_api_key': Config.COINGECKO_API_KEY
                    },
                    timeout=10
                )
                response.raise_for_status()
                data = response.json()
                
                # For USDT as base, rate is 1/usd_price 
                if coin_id in data and 'usd' in data[coin_id]:
                    usd_price = data[coin_id]['usd']
                    if usd_price > 0:
                        rates[currency] = 1 / usd_price
            
            return rates
        else:
            # For other base currencies, get their USD rate first
            base_id = _get_coin_id(base_currency)
            base_response = requests.get(
                f'{COINGECKO_API_URL}/simple/price',
                params={
                    'ids': base_id,
                    'vs_currencies': 'usd',
                    'x_cg_pro_api_key': Config.COINGECKO_API_KEY
                },
                timeout=10
            )
            base_response.raise_for_status()
            base_data = base_response.json()
            
            if base_id not in base_data or 'usd' not in base_data[base_id]:
                logger.error(f"Could not get USD price for {base_currency}")
                return {}
                
            base_usd_price = base_data[base_id]['usd']
            
            # Then get USD rates for quote currencies
            rates = {}
            for currency in quote_currencies:
                coin_id = _get_coin_id(currency)
                response = requests.get(
                    f'{COINGECKO_API_URL}/simple/price',
                    params={
                        'ids': coin_id,
                        'vs_currencies': 'usd',
                        'x_cg_pro_api_key': Config.COINGECKO_API_KEY
                    },
                    timeout=10
                )
                response.raise_for_status()
                data = response.json()
                
                if coin_id in data and 'usd' in data[coin_id]:
                    quote_usd_price = data[coin_id]['usd']
                    # Calculate the cross rate: quote_currency/base_currency
                    if base_usd_price > 0:
                        rates[currency] = quote_usd_price / base_usd_price
            
            return rates
                
    except requests.RequestException as e:
        logger.error(f"Error fetching exchange rates: {str(e)}")
        return {}

def get_coin_details(symbol):
    """
    Get detailed information for a cryptocurrency.
    
    Args:
        symbol: Cryptocurrency symbol (e.g., 'BTC')
    
    Returns:
        Dictionary with coin details
    """
    try:
        # Get coin ID from symbol
        coin_id = _get_coin_id(symbol)
        
        # Fetch coin data from CoinGecko
        response = requests.get(
            f'{COINGECKO_API_URL}/coins/{coin_id}',
            params={
                'localization': 'false',
                'tickers': 'false',
                'market_data': 'true',
                'community_data': 'false',
                'developer_data': 'false',
                'x_cg_pro_api_key': Config.COINGECKO_API_KEY
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
        logger.error(f"Error fetching coin details: {str(e)}")
        raise RuntimeError(f"Unable to fetch data for {symbol}. Please try again later.")

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
        # Calculate page number for API request
        page = offset // limit + 1
        
        # Fetch market data from CoinGecko
        response = requests.get(
            f'{COINGECKO_API_URL}/coins/markets',
            params={
                'vs_currency': 'usd',
                'order': 'market_cap_desc',
                'per_page': limit,
                'page': page,
                'sparkline': 'false',
                'x_cg_pro_api_key': Config.COINGECKO_API_KEY
            },
            timeout=10
        )
        
        response.raise_for_status()
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
        logger.error(f"Error fetching market overview: {str(e)}")
        raise RuntimeError("Unable to fetch market data. Please try again later.") 

def get_chart_data(symbol, interval='1d', limit=100):
    """
    Get historical chart data for a cryptocurrency.
    
    Args:
        symbol: Cryptocurrency symbol (e.g., 'BTC')
        interval: Time interval ('1d', '7d', '14d', '30d', '90d', '180d', '365d', 'max')
        limit: Number of data points to return
    
    Returns:
        List of OHLCV data points
    """
    try:
        # Get coin ID from symbol
        coin_id = _get_coin_id(symbol)
        
        # Map interval to days parameter for CoinGecko
        days_map = {
            '1d': 1,
            '7d': 7,
            '14d': 14,
            '30d': 30,
            '90d': 90,
            '180d': 180,
            '365d': 365,
            'max': 'max'
        }
        
        days = days_map.get(interval, 30)
        
        # Fetch market chart data from CoinGecko
        response = requests.get(
            f'{COINGECKO_API_URL}/coins/{coin_id}/market_chart',
            params={
                'vs_currency': 'usd',
                'days': days,
                'interval': 'daily',
                'x_cg_pro_api_key': Config.COINGECKO_API_KEY
            },
            timeout=10
        )
        
        response.raise_for_status()
        data = response.json()
        
        # Transform prices data to OHLCV-like format
        # CoinGecko returns [timestamp, price] pairs
        result = []
        
        # Get price data points
        prices = data.get('prices', [])
        
        # Get volumes if available
        volumes = data.get('total_volumes', [])
        volumes_dict = {item[0]: item[1] for item in volumes} if volumes else {}
        
        for i, price_point in enumerate(prices):
            timestamp = price_point[0]  # Timestamp in milliseconds
            price = price_point[1]      # Price at that timestamp
            
            # For proper OHLCV format, we need open, high, low, close
            # Since we only have one price per day, use it for all values
            volume = volumes_dict.get(timestamp, 0)
            
            # Skip if we already have enough data points
            if i >= limit:
                break
                
            # Create OHLCV candle
            candle = [
                timestamp,  # timestamp
                price,      # open
                price,      # high 
                price,      # low
                price,      # close
                volume      # volume
            ]
            
            result.append(candle)
        
        return result
    except requests.RequestException as e:
        logger.error(f"Error fetching chart data: {str(e)}")
        raise RuntimeError(f"Unable to fetch chart data for {symbol}. Please try again later.")

def get_current_price(currency_pair):
    """
    Get the current price for a trading pair.
    
    Args:
        currency_pair: Trading pair (e.g., 'BTC/USDT')
    
    Returns:
        Current price as a float
    """
    try:
        # Extract base currency from the pair format
        parts = currency_pair.split('/')
        if len(parts) != 2:
            logger.error(f"Invalid currency pair format: {currency_pair}")
            return 0
            
        base_currency = parts[0]  # e.g., 'BTC' from 'BTC/USDT'
        quote_currency = parts[1]  # e.g., 'USDT' from 'BTC/USDT'
        
        # Map quote currency properly - CoinGecko uses 'usd' for USDT
        vs_currency = quote_currency.lower()
        if vs_currency == 'usdt':
            vs_currency = 'usd'  # CoinGecko uses USD as equivalent to USDT
        
        # Get coin ID for the base currency
        coin_id = _get_coin_id(base_currency)
        
        # Fetch current price from CoinGecko
        response = requests.get(
            f'{COINGECKO_API_URL}/simple/price',
            params={
                'ids': coin_id,
                'vs_currencies': vs_currency,
                'x_cg_pro_api_key': Config.COINGECKO_API_KEY
            },
            timeout=10
        )
        
        response.raise_for_status()
        data = response.json()
        
        # Extract price from response
        if coin_id in data and vs_currency in data[coin_id]:
            return float(data[coin_id][vs_currency])
        else:
            logger.error(f"Could not find price for {currency_pair} in API response. Response: {data}")
            # Try fallback using market data
            try:
                # Fetch coin market data which includes price
                market_response = requests.get(
                    f'{COINGECKO_API_URL}/coins/markets',
                    params={
                        'vs_currency': vs_currency,
                        'ids': coin_id,
                        'x_cg_pro_api_key': Config.COINGECKO_API_KEY
                    },
                    timeout=10
                )
                market_response.raise_for_status()
                market_data = market_response.json()
                
                if market_data and len(market_data) > 0 and 'current_price' in market_data[0]:
                    return float(market_data[0]['current_price'])
                else:
                    logger.error(f"Fallback also failed to find price for {currency_pair}")
                    return 0
            except Exception as e:
                logger.error(f"Error in fallback price fetch: {str(e)}")
                return 0
            
    except requests.RequestException as e:
        logger.error(f"Error fetching current price: {str(e)}")
        return 0
    except (KeyError, IndexError, ValueError) as e:
        logger.error(f"Error parsing price data: {str(e)}")
        return 0
    except Exception as e:
        logger.error(f"Unexpected error in get_current_price: {str(e)}")
        return 0

def get_popular_coins(limit=5):
    """
    Get a list of popular coins.
    
    Args:
        limit: Number of coins to return
    
    Returns:
        List of popular cryptocurrency details
    """
    try:
        # Fetch popular coins from CoinGecko (based on market cap)
        response = requests.get(
            f'{COINGECKO_API_URL}/coins/markets',
            params={
                'vs_currency': 'usd',
                'order': 'market_cap_desc',
                'per_page': limit,
                'page': 1,
                'sparkline': 'false',
                'x_cg_pro_api_key': Config.COINGECKO_API_KEY
            },
            timeout=10
        )
        
        response.raise_for_status()
        data = response.json()
        
        # Transform data to the expected format
        result = []
        for coin in data:
            result.append({
                'symbol': coin['symbol'].upper(),
                'name': coin['name'],
                'price': coin['current_price'],
                'change_24h': coin['price_change_percentage_24h']
            })
        
        return result
    except requests.RequestException as e:
        logger.error(f"Error fetching popular coins: {str(e)}")
        raise RuntimeError("Unable to fetch popular coins. Please try again later.")

def get_new_listings(limit=5):
    """
    Get a list of new cryptocurrency listings.
    
    Args:
        limit: Number of new listings to return
    
    Returns:
        List of new cryptocurrency listings
    """
    try:
        # Fetch new listings from CoinGecko
        response = requests.get(
            f'{COINGECKO_API_URL}/coins/markets',
            params={
                'vs_currency': 'usd',
                'order': 'id_asc',  # New coins typically have higher IDs
                'per_page': 250,    # Fetch a larger set to filter
                'page': 1,
                'sparkline': 'false',
                'x_cg_pro_api_key': Config.COINGECKO_API_KEY
            },
            timeout=10
        )
        
        response.raise_for_status()
        all_coins = response.json()
        
        # Get current time in UTC with no timezone info
        current_time_naive = datetime.utcnow()
        one_year_ago = current_time_naive - timedelta(days=365)
        
        # Sort coins by the 'last_updated' field to get the most recently added ones
        # Convert date strings to datetime objects for proper sorting
        for coin in all_coins:
            try:
                # Check if last_updated is None or empty
                if not coin.get('last_updated'):
                    # Use a default old date for sorting
                    coin['last_updated_datetime'] = one_year_ago
                else:
                    # Try to parse the date string (handle different formats)
                    last_updated = coin['last_updated']
                    if isinstance(last_updated, str):
                        # Parse the date string to datetime object
                        if 'Z' in last_updated:
                            # Convert to naive datetime by removing timezone info
                            dt = datetime.strptime(last_updated.replace('Z', ''), '%Y-%m-%dT%H:%M:%S.%f')
                        elif '+' in last_updated:
                            # Parse with timezone, then convert to naive
                            dt = datetime.strptime(last_updated.split('+')[0], '%Y-%m-%dT%H:%M:%S.%f')
                        else:
                            # Regular ISO format without timezone
                            dt = datetime.strptime(last_updated, '%Y-%m-%dT%H:%M:%S.%f')
                        
                        coin['last_updated_datetime'] = dt
                    else:
                        # If it's not a string, use fallback
                        coin['last_updated_datetime'] = one_year_ago
            except (ValueError, TypeError, AttributeError) as e:
                logger.warning(f"Error parsing date '{coin.get('last_updated')}': {str(e)}")
                # If parsing fails, use the fallback date
                coin['last_updated_datetime'] = one_year_ago
        
        # Sort by last_updated in descending order
        # Use a safe getter function with default value for missing keys
        def get_date(coin_data):
            date = coin_data.get('last_updated_datetime')
            return date if date is not None else one_year_ago
            
        all_coins.sort(key=get_date, reverse=True)
        
        # Take only the required number of coins
        new_coins = all_coins[:limit]
        
        # Transform data to the expected format
        result = []
        for coin in new_coins:
            # Handle potential missing data
            price_change = coin.get('price_change_percentage_24h')
            if price_change is None:
                price_change = 0.0
                
            result.append({
                'symbol': coin.get('symbol', '').upper(),
                'name': coin.get('name', 'Unknown'),
                'price': coin.get('current_price', 0),
                'change_24h': price_change
            })
        
        return result
    except requests.RequestException as e:
        logger.error(f"Error fetching new listings: {str(e)}")
        # Return empty list as fallback
        return []
    except Exception as e:
        logger.error(f"Unexpected error in get_new_listings: {str(e)}")
        # Return empty list as fallback
        return []