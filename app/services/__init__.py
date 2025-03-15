# app/services/__init__.py
"""
Business logic services initialization.
Import all service functions here to make them available throughout the application.
"""
from app.services.auth_service import generate_otp, send_otp_email, send_otp_sms, verify_otp, register_user
from app.services.market_service import (
    get_market_data, get_coin_data, get_chart_data, 
    get_popular_coins, get_new_listings, get_current_price
)
from app.services.wallet_service import (
    generate_blockchain_address, validate_address, get_wallet_balance,
    create_wallet, add_balance, subtract_balance, transfer_balance,
    convert_currency, get_conversion_rate
)
# Additional imports from wallet_service_part2
from app.services.wallet_service_part2 import (
    create_deposit_transaction, create_withdrawal_transaction,
    create_transfer_transaction, create_convert_transaction,
    create_payment_transactions, get_transaction_history,
    get_deposit_address, verify_deposit, process_withdrawal,
    get_user_portfolio
)