# init_db.py
from app import create_app, db

def initialize_database():
    """Initialize the database and create all tables"""
    app = create_app()
    with app.app_context():
        # Create all tables
        db.create_all()
        print("Database tables created successfully!")

if __name__ == "__main__":
    initialize_database()