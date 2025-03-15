# app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from .config import Config

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
bcrypt = Bcrypt()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    CORS(app)
    
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'
    
    # Register blueprints
    from app.routes.auth import auth
    from app.routes.user import user
    from app.routes.wallet import wallet
    from app.routes.market import market
    from app.routes.trade import trade
    from app.routes.admin import admin
    
    app.register_blueprint(auth, url_prefix='/auth')
    app.register_blueprint(user, url_prefix='/user')
    app.register_blueprint(wallet, url_prefix='/wallet')
    app.register_blueprint(market, url_prefix='/market')
    app.register_blueprint(trade, url_prefix='/trade')
    app.register_blueprint(admin, url_prefix='/admin')
    
    return app

# app/config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-for-development'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-dev-key'
    JWT_ACCESS_TOKEN_EXPIRES = 3600  # 1 hour
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 25)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    CRYPTO_API_KEY = os.environ.get('CRYPTO_API_KEY')
    UPLOAD_FOLDER = os.path.join('app', 'static', 'uploads')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

# run.py
from app import create_app, db

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)