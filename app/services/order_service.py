# app/services/order_service.py
from datetime import datetime
from app import db
from app.models.order import Order
from app.models.wallet import Wallet
from app.models.transaction import Transaction
from app.services.market_service import get_current_price_service as get_current_price
import logging

logger = logging.getLogger(__name__)

def process_open_orders():
    """
    Process all open orders to check if they can be filled based on current market prices.
    This function would typically be called from a scheduled task or background worker.
    """
    try:
        # Get all open orders
        open_orders = Order.query.filter_by(status='open').all()
        
        if not open_orders:
            logger.info("No open orders to process")
            return
            
        logger.info(f"Processing {len(open_orders)} open orders")
        
        for order in open_orders:
            try:
                # Get current price for the currency pair
                current_price = get_current_price(order.currency_pair)
                
                if current_price <= 0:
                    logger.warning(f"Could not get valid price for {order.currency_pair}")
                    continue
                
                # Check if order conditions are met
                should_fill = False
                
                if order.order_type == 'limit':
                    # For buy limit orders, fill when price drops to or below limit price
                    if order.side == 'buy' and current_price <= order.price:
                        should_fill = True
                    # For sell limit orders, fill when price rises to or above limit price
                    elif order.side == 'sell' and current_price >= order.price:
                        should_fill = True
                
                elif order.order_type == 'stop':
                    # For buy stop orders, fill when price rises to or above stop price
                    if order.side == 'buy' and current_price >= order.price:
                        should_fill = True
                    # For sell stop orders, fill when price drops to or below stop price
                    elif order.side == 'sell' and current_price <= order.price:
                        should_fill = True
                
                # If conditions are met, fill the order
                if should_fill:
                    logger.info(f"Filling order {order.id} at price {current_price}")
                    fill_order(order, current_price)
                    
            except Exception as e:
                logger.error(f"Error processing order {order.id}: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error in process_open_orders: {str(e)}")

def fill_order(order, execution_price):
    """
    Fill an order at the specified execution price.
    
    Args:
        order: Order object to fill
        execution_price: Price at which the order is executed
    
    Returns:
        Boolean indicating success or failure
    """
    try:
        # Extract currencies from the pair
        currency_parts = order.currency_pair.split('/')
        if len(currency_parts) != 2:
            logger.error(f"Invalid currency pair format: {order.currency_pair}")
            return False
            
        base_currency, quote_currency = currency_parts
        
        # Calculate total cost/proceeds
        total_cost = execution_price * order.amount
        
        # Update order status
        order.status = 'filled'
        order.filled_amount = order.amount
        order.filled_at = datetime.utcnow()
        
        # Handle wallet updates
        if order.side == 'buy':
            # When buying, add base currency to wallet
            base_wallet = Wallet.query.filter_by(user_id=order.user_id, currency=base_currency).first()
            
            if not base_wallet:
                base_wallet = Wallet(user_id=order.user_id, currency=base_currency, spot_balance=0)
                db.session.add(base_wallet)
            
            base_wallet.spot_balance += order.amount
            
            # If the execution price is lower than the limit price, refund the difference
            if execution_price < order.price:
                quote_wallet = Wallet.query.filter_by(user_id=order.user_id, currency=quote_currency).first()
                if quote_wallet:
                    refund_amount = (order.price - execution_price) * order.amount
                    quote_wallet.spot_balance += refund_amount
        
        elif order.side == 'sell':
            # When selling, add quote currency to wallet
            quote_wallet = Wallet.query.filter_by(user_id=order.user_id, currency=quote_currency).first()
            
            if not quote_wallet:
                quote_wallet = Wallet(user_id=order.user_id, currency=quote_currency, spot_balance=0)
                db.session.add(quote_wallet)
            
            quote_wallet.spot_balance += total_cost
        
        # Create transaction records
        transaction = Transaction(
            user_id=order.user_id,
            transaction_type='trade',
            status='completed',
            currency=base_currency if order.side == 'buy' else quote_currency,
            amount=order.amount if order.side == 'buy' else total_cost,
            fee=0,  # You could implement trading fees here
            from_wallet='spot',
            to_wallet='spot',
            notes=f"{order.side.capitalize()} {order.amount} {base_currency} at {execution_price} {quote_currency} per {base_currency}"
        )
        
        db.session.add(transaction)
        db.session.commit()
        
        logger.info(f"Order {order.id} filled successfully at price {execution_price}")
        return True
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error filling order {order.id}: {str(e)}")
        return False