# app/utils/__init__.py
"""
Utility functions initialization.
Import all utility functions here to make them available throughout the application.
"""
from app.utils.validators import validate_email, validate_password, validate_phone
from app.utils.helpers import generate_unique_id, format_currency_amount, format_datetime
from app.utils.crypto_api import get_exchange_rates, get_coin_details, get_market_overview