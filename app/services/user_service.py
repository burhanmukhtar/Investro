# app/services/user_service.py
"""
User management business logic.
Handles user profile, verification, and related operations.
"""
import os
from datetime import datetime
from werkzeug.utils import secure_filename
from app import db
from app.models.user import User, VerificationDocument
from app.config import Config
import logging

def get_user_by_id(user_id):
    """Get user by ID."""
    return User.query.get(user_id)

def get_user_by_email(email):
    """Get user by email."""
    return User.query.filter_by(email=email).first()

def get_user_by_username(username):
    """Get user by username."""
    return User.query.filter_by(username=username).first()

def get_user_by_unique_id(unique_id):
    """Get user by unique ID."""
    return User.query.filter_by(unique_id=unique_id).first()

def update_user_profile(user, data):
    """
    Update user profile information.
    
    Args:
        user: User object to update
        data: Dictionary containing updated fields
    
    Returns:
        Tuple of (success, message)
    """
    try:
        # Update fields if they exist in the data
        if 'username' in data and not user.is_verified:
            # Check if username is already taken
            existing_user = get_user_by_username(data['username'])
            if existing_user and existing_user.id != user.id:
                return False, "Username already taken."
            user.username = data['username']
        
        # Save changes
        db.session.commit()
        
        return True, "Profile updated successfully."
    except Exception as e:
        db.session.rollback()
        return False, f"Error updating profile: {str(e)}"

def update_profile_picture(user, file):
    """
    Upload and update user's profile picture.
    
    Args:
        user: User object to update
        file: Uploaded file object
    
    Returns:
        Tuple of (success, message)
    """
    try:
        if file and file.filename:
            # Validate file type
            allowed_extensions = {'png', 'jpg', 'jpeg'}
            if '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in allowed_extensions:
                # Generate secure filename
                filename = secure_filename(f"{user.id}_{file.filename}")
                
                # Ensure directory exists
                upload_dir = os.path.join(Config.UPLOAD_FOLDER, 'profile_pictures')
                os.makedirs(upload_dir, exist_ok=True)
                
                # Save file
                filepath = os.path.join(upload_dir, filename)
                file.save(filepath)
                
                # Update user's profile image
                user.profile_image = filename
                db.session.commit()
                
                return True, "Profile picture updated successfully."
            else:
                return False, "Invalid file type. Allowed types: PNG, JPG, JPEG."
        else:
            return False, "No file provided."
    except Exception as e:
        db.session.rollback()
        return False, f"Error updating profile picture: {str(e)}"

def change_password(user, current_password, new_password):
    """
    Change user's password.
    
    Args:
        user: User object
        current_password: Current password for verification
        new_password: New password to set
    
    Returns:
        Tuple of (success, message)
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        if not user.check_password(current_password):
            return False, "Current password is incorrect."
        
        user.set_password(new_password)
        db.session.commit()
        
        # Send security alert email
        try:
            from app.services.email_notification_service import send_security_alert
            
            # Get request information if available
            try:
                from flask import request
                ip_address = request.remote_addr or "Unknown"
                user_agent = request.headers.get('User-Agent', 'Unknown browser')
            except:
                ip_address = "Unknown"
                user_agent = "Unknown browser"
            
            send_security_alert(
                user=user,
                action="Password Change",
                ip_address=ip_address,
                device_info=user_agent
            )
            logger.info(f"Password change security alert sent to user {user.id}")
        except Exception as e:
            logger.error(f"Error sending password change security alert: {str(e)}")
        
        return True, "Password changed successfully."
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error changing password: {str(e)}")
        return False, f"Error changing password: {str(e)}"

def set_withdrawal_pin(user, pin):
    """
    Set or change user's withdrawal PIN.
    
    Args:
        user: User object
        pin: 6-digit PIN
    
    Returns:
        Tuple of (success, message)
    """
    try:
        if not pin.isdigit() or len(pin) != 6:
            return False, "PIN must be a 6-digit number."
        
        user.set_withdrawal_pin(pin)
        db.session.commit()
        
        return True, "Withdrawal PIN set successfully."
    except Exception as e:
        db.session.rollback()
        return False, f"Error setting withdrawal PIN: {str(e)}"

def submit_verification_document(user, document_type, file):
    """
    Submit a verification document for KYC.
    
    Args:
        user: User object
        document_type: Type of document being submitted
        file: Uploaded file object
    
    Returns:
        Tuple of (success, message)
    """
    try:
        if file and file.filename:
            # Validate file type
            allowed_extensions = {'png', 'jpg', 'jpeg', 'pdf'}
            if '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in allowed_extensions:
                # Generate secure filename
                filename = secure_filename(f"{user.id}_{document_type}_{file.filename}")
                
                # Ensure directory exists
                upload_dir = os.path.join(Config.UPLOAD_FOLDER, 'verification_documents')
                os.makedirs(upload_dir, exist_ok=True)
                
                # Save file
                filepath = os.path.join(upload_dir, filename)
                file.save(filepath)
                
                # Create verification document record
                doc = VerificationDocument(
                    user_id=user.id,
                    document_type=document_type,
                    document_path=filename
                )
                
                # Update user's verification status
                user.verification_status = 'pending'
                
                db.session.add(doc)
                db.session.commit()
                
                return True, "Verification document submitted successfully."
            else:
                return False, "Invalid file type. Allowed types: PNG, JPG, JPEG, PDF."
        else:
            return False, "No file provided."
    except Exception as e:
        db.session.rollback()
        return False, f"Error submitting verification document: {str(e)}"

def get_referred_users(user):
    """
    Get users referred by the given user.
    
    Args:
        user: User object
    
    Returns:
        List of users referred by the user
    """
    return User.query.filter_by(referred_by=user.referral_code).all()

def get_verification_documents(user_id):
    """
    Get verification documents for a user.
    
    Args:
        user_id: User ID
    
    Returns:
        List of verification documents
    """
    return VerificationDocument.query.filter_by(user_id=user_id).order_by(VerificationDocument.submitted_at.desc()).all()