# app/__init__.py
from flask import Flask, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, current_user
from flask_mail import Mail
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime
import re

# Initialize extensions
db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
mail = Mail()
migrate = Migrate()
csrf = CSRFProtect()

def add_verification_middleware(app):
    """Add middleware to check verification requirements for certain routes"""
    
    # Routes that require verification
    restricted_routes = [
        'wallet.deposit', 'wallet.withdraw', 'wallet.convert', 'wallet.pay',
        'wallet.transfer', 'trade.signals', 'trade.positions', 'trade.follow_signal',
        'trade.close_position', 'trade.orders', 'trade.place_order', 'trade.cancel_order'
    ]
    
    @app.before_request
    def check_verification_requirements():
        # Skip for non-authenticated users
        if not current_user.is_authenticated:
            return
            
        # Skip for certain routes
        if request.endpoint in ('user.verification', 'user.hide_verification_popup', 
                              'auth.logout', 'static', 'user.profile'):
            return
            
        # Check if the route is in restricted list
        if request.endpoint in restricted_routes:
            if not current_user.is_verified:
                flash('Verification required to access this feature. Please complete your verification.', 'warning')
                return redirect(url_for('user.verification'))

def create_app(config_class='app.config.Config'):
    app = Flask(__name__)
    
    app.config.from_object(config_class)

    # Initialize extensions with app
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    # Configure login
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'
    login_manager.login_message = 'Please log in to access this page.'

    # Add verification middleware
    add_verification_middleware(app)

    # Register blueprints
    from app.routes.admin import admin
    from app.routes.auth import auth
    from app.routes.market import market
    from app.routes.trade import trade
    from app.routes.user import user
    from app.routes.wallet import wallet
    from app.models.deposit_address import DepositAddress

    app.register_blueprint(admin, url_prefix='/admin')
    app.register_blueprint(auth, url_prefix='/auth')
    app.register_blueprint(market, url_prefix='/market')
    app.register_blueprint(trade, url_prefix='/trade')
    app.register_blueprint(user, url_prefix='/user')
    app.register_blueprint(wallet, url_prefix='/wallet')

    # Add template context processor for current date
    @app.context_processor
    def inject_now():
        return {'now': datetime.utcnow()}

    # Add root route
    @app.route('/')
    def home():
        return redirect(url_for('auth.login'))

    # Setup logging
    if not app.debug and not app.testing:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/investro.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info('Investro startup')

    return app

# Import models for proper DB initialization
from app.models.user import User, VerificationDocument
from app.models.wallet import Wallet
from app.models.transaction import Transaction
from app.models.user_settings import UserSettings
from app.models.support_ticket import SupportTicket, TicketResponse  # Add this line