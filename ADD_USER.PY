# add_user.py
from app import create_app, db, bcrypt
from app.models.user import User
import random
import string

def add_admin_user(username, email, phone, password):
    """Add an admin user to the database"""
    # Create app context
    app = create_app()
    with app.app_context():
        # Check if user already exists
        existing_user = User.query.filter((User.username == username) |
                                         (User.email == email) |
                                         (User.phone == phone)).first()
        if existing_user:
            print(f"User with username '{username}', email '{email}', or phone '{phone}' already exists.")
            return False
            
        # Create the user
        # Based on your User model, we should pass the raw password to the constructor
        # The User model will handle generating unique_id and referral_code
        user = User(
            username=username,
            email=email,
            phone=phone,
            password=password  # The User model will hash this internally
        )
            
        # Set admin status
        user.is_admin = True
        user.is_verified = True
        user.verification_status = 'approved'
            
        # Add to database
        db.session.add(user)
        try:
            db.session.commit()
            print(f"Admin user '{username}' created successfully!")
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Error creating user: {str(e)}")
            return False

if __name__ == "__main__":
    # Default admin credentials
    username = "nullbyte"
    email = "nullbyte0031@gmail.com"
    phone = "+12345678455404"
    password = "Naruto@007"
    
    # You can override these with command line arguments if needed
    import sys
    if len(sys.argv) >= 5:
        username = sys.argv[1]
        email = sys.argv[2]
        phone = sys.argv[3]
        password = sys.argv[4]
    
    add_admin_user(username, email, phone, password)