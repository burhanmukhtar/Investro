# app/routes/__init__.py
"""
API routes initialization.
Import all route blueprints here to make them available for registering with the Flask app.
"""
from app.routes.auth import auth
from app.routes.user import user
from app.routes.wallet import wallet
from app.routes.market import market
from app.routes.trade import trade
from app.routes.admin import admin

# List of all blueprints to register with the app
blueprints = [auth, user, wallet, market, trade, admin]