# app/utils/helpers.py
"""
Helper utility functions.
General-purpose functions used throughout the application.
"""
import random
import string
import uuid
from datetime import datetime

def generate_unique_id(prefix=None, length=8):
    """
    Generate a unique ID with an optional prefix.
    
    Args:
        prefix: Optional string prefix for the ID
        length: Length of the random part of the ID
    
    Returns:
        Unique ID string
    """
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
    
    if prefix:
        return f"{prefix}{random_part}"
    else:
        return random_part

def generate_transaction_id():
    """
    Generate a unique transaction ID based on UUID.
    
    Returns:
        Transaction ID string
    """
    return str(uuid.uuid4())

def format_currency_amount(amount, currency=None, precision=None):
    """
    Format a currency amount with appropriate precision.
    
    Args:
        amount: Numeric amount to format
        currency: Optional currency code to determine precision
        precision: Optional fixed precision (overrides currency-based precision)
    
    Returns:
        Formatted amount string
    """
    # Set precision based on currency if not explicitly specified
    if precision is None:
        if currency in ['BTC']:
            precision = 8
        elif currency in ['ETH', 'BNB']:
            precision = 6
        elif currency in ['USDT', 'USDC', 'DAI']:
            precision = 2
        else:
            precision = 4
    
    # Format the amount
    formatted = f"{float(amount):.{precision}f}"
    
    # Remove trailing zeros after decimal point
    if '.' in formatted:
        formatted = formatted.rstrip('0').rstrip('.') if '.' in formatted else formatted
    
    return formatted

def format_datetime(dt, format_str='%Y-%m-%d %H:%M:%S'):
    """
    Format a datetime object as a string.
    
    Args:
        dt: Datetime object to format
        format_str: Format string for strftime
    
    Returns:
        Formatted datetime string
    """
    if isinstance(dt, datetime):
        return dt.strftime(format_str)
    return str(dt)

def calculate_percentage_change(old_value, new_value):
    """
    Calculate percentage change between two values.
    
    Args:
        old_value: Original value
        new_value: New value
    
    Returns:
        Percentage change as a float
    """
    if old_value == 0:
        return 0
    
    return ((new_value - old_value) / abs(old_value)) * 100

def parse_datetime(datetime_str, format_str='%Y-%m-%d %H:%M:%S'):
    """
    Parse a datetime string into a datetime object.
    
    Args:
        datetime_str: Datetime string to parse
        format_str: Format string for strptime
    
    Returns:
        Datetime object or None if parsing fails
    """
    try:
        return datetime.strptime(datetime_str, format_str)
    except (ValueError, TypeError):
        return None

def truncate_string(string, max_length=50, suffix='...'):
    """
    Truncate a string to the specified maximum length.
    
    Args:
        string: String to truncate
        max_length: Maximum length before truncating
        suffix: String to append when truncating
    
    Returns:
        Truncated string
    """
    if len(string) <= max_length:
        return string
    
    return string[:max_length - len(suffix)] + suffix

def mask_sensitive_data(data, mask_char='*'):
    """
    Mask sensitive data like email addresses and phone numbers.
    
    Args:
        data: String containing sensitive data
        mask_char: Character to use for masking
    
    Returns:
        Masked string
    """
    if not data:
        return data
    
    # Email masking (show first 2 chars, then mask until @, then show domain)
    if '@' in data:
        parts = data.split('@')
        username = parts[0]
        domain = parts[1]
        
        if len(username) <= 2:
            masked_username = username
        else:
            masked_username = username[:2] + mask_char * (len(username) - 2)
        
        return f"{masked_username}@{domain}"
    
    # Phone number masking (show last 4 digits, mask the rest)
    elif any(c.isdigit() for c in data):
        digits = ''.join(c for c in data if c.isdigit())
        if len(digits) <= 4:
            return data
        
        visible_part = digits[-4:]
        masked_part = mask_char * (len(digits) - 4)
        
        # Try to preserve the format
        result = data
        for d in digits[:-4]:
            result = result.replace(d, mask_char, 1)
        
        return result
    
    # Generic masking (show first and last char, mask the rest)
    elif len(data) > 2:
        return data[0] + mask_char * (len(data) - 2) + data[-1]
    
    return data

def generate_random_code(length=6, use_letters=False):
    """
    Generate a random code for verification or reference purposes.
    
    Args:
        length: Length of the code
        use_letters: Whether to include letters or just digits
    
    Returns:
        Random code string
    """
    if use_letters:
        chars = string.ascii_uppercase + string.digits
    else:
        chars = string.digits
    
    return ''.join(random.choices(chars, k=length))

def is_valid_json(json_str):
    """
    Check if a string is valid JSON.
    
    Args:
        json_str: String to check
    
    Returns:
        Boolean indicating if the string is valid JSON
    """
    import json
    
    try:
        json.loads(json_str)
        return True
    except (json.JSONDecodeError, TypeError):
        return False