# app/utils/validators.py
"""
Input validation functions.
Used for validating user inputs before processing them.
"""
import re
from decimal import Decimal

def validate_email(email):
    """
    Validate email format.
    
    Args:
        email: Email string to validate
    
    Returns:
        Boolean indicating if email is valid
    """
    # Simple regex for email validation
    pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return bool(re.match(pattern, email))

def validate_password(password):
    """
    Validate password strength.
    Password must be at least 8 characters and include at least:
    - One uppercase letter
    - One lowercase letter
    - One number
    
    Args:
        password: Password string to validate
    
    Returns:
        Boolean indicating if password is valid
    """
    # Check length
    if len(password) < 8:
        return False
    
    # Check for uppercase letter
    if not any(char.isupper() for char in password):
        return False
    
    # Check for lowercase letter
    if not any(char.islower() for char in password):
        return False
    
    # Check for number
    if not any(char.isdigit() for char in password):
        return False
    
    return True

def validate_phone(phone):
    """
    Validate phone number format.
    Accepts various international formats.
    
    Args:
        phone: Phone number string to validate
    
    Returns:
        Boolean indicating if phone number is valid
    """
    # Strip spaces and other non-digit characters except + at the beginning
    phone = phone.strip()
    
    # Check for basic phone number pattern
    # This allows for international format with + or without it
    pattern = r'^(\+\d{1,3})?[\s.-]?\(?\d{1,4}\)?[\s.-]?\d{1,4}[\s.-]?\d{1,9}$'
    
    # Make sure there's at least 7 digits in total
    digit_count = sum(c.isdigit() for c in phone)
    
    return bool(re.match(pattern, phone)) and digit_count >= 7

def validate_amount(amount, min_value=0, max_value=None):
    """
    Validate a numeric amount.
    
    Args:
        amount: Amount to validate (string or number)
        min_value: Minimum allowed value (inclusive)
        max_value: Maximum allowed value (inclusive), or None for no upper limit
    
    Returns:
        Boolean indicating if amount is valid
    """
    try:
        # Convert to Decimal for precise comparison
        decimal_amount = Decimal(str(amount))
        
        # Check minimum value
        if decimal_amount < Decimal(str(min_value)):
            return False
        
        # Check maximum value if specified
        if max_value is not None and decimal_amount > Decimal(str(max_value)):
            return False
        
        return True
    except (ValueError, TypeError, decimal.InvalidOperation):
        return False

def validate_withdrawal_pin(pin):
    """
    Validate withdrawal PIN.
    PIN must be exactly 6 digits.
    
    Args:
        pin: PIN string to validate
    
    Returns:
        Boolean indicating if PIN is valid
    """
    return bool(pin.isdigit() and len(pin) == 6)

def validate_blockchain_address(address, currency, chain):
    """
    Validate blockchain address format for the given currency and chain.
    
    Args:
        address: Blockchain address to validate
        currency: Cryptocurrency (e.g., 'BTC', 'ETH')
        chain: Blockchain network (e.g., 'TRC20', 'ERC20')
    
    Returns:
        Boolean indicating if address is valid
    """
    # Different validation patterns based on currency and chain
    if chain == 'TRC20':
        # TRON addresses start with T and are 34 characters long
        return bool(re.match(r'^T[A-Za-z0-9]{33}$', address))
    
    elif chain == 'ERC20':
        # Ethereum addresses start with 0x and are 42 characters long
        return bool(re.match(r'^0x[0-9a-fA-F]{40}$', address))
    
    elif currency == 'BTC':
        # Bitcoin addresses can be legacy (1), segwit (3), or bech32 (bc1)
        legacy_pattern = r'^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$'
        bech32_pattern = r'^bc1[a-zA-Z0-9]{39,59}$'
        return bool(re.match(legacy_pattern, address) or re.match(bech32_pattern, address))
    
    # For other currencies, just check a generic format
    # This should be expanded with specific validation for each currency
    return len(address) >= 30

def sanitize_input(input_string):
    """
    Sanitize a string input to prevent XSS and other injection attacks.
    
    Args:
        input_string: String to sanitize
    
    Returns:
        Sanitized string
    """
    # Replace potentially dangerous characters
    sanitized = input_string.replace('<', '&lt;').replace('>', '&gt;')
    
    # Remove any script tags (case-insensitive)
    sanitized = re.sub(r'(?i)<script.*?>.*?</script>', '', sanitized)
    
    # Remove any on* event handlers
    sanitized = re.sub(r'(?i)on\w+\s*=\s*["\'][^"\']*["\']', '', sanitized)
    
    return sanitized