# app/services/support_service.py
import os
import random
import string
import logging
from datetime import datetime
from werkzeug.utils import secure_filename
from app import db
from app.models.support_ticket import SupportTicket, TicketResponse
from app.models.user import User
from app.config import Config
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

def generate_ticket_number():
    """Generate a unique ticket number."""
    prefix = "TKT"
    random_part = ''.join(random.choices(string.digits, k=7))
    ticket_number = f"{prefix}{random_part}"
    
    # Check if ticket number already exists
    while SupportTicket.query.filter_by(ticket_number=ticket_number).first():
        random_part = ''.join(random.choices(string.digits, k=7))
        ticket_number = f"{prefix}{random_part}"
    
    return ticket_number

def create_support_ticket(user_id, category, subject, message, attachment=None):
    """
    Create a new support ticket.
    
    Args:
        user_id: User ID
        category: Ticket category
        subject: Ticket subject
        message: Ticket message
        attachment: Optional file attachment
    
    Returns:
        Tuple of (success, message, ticket)
    """
    try:
        # Generate unique ticket number
        ticket_number = generate_ticket_number()
        
        # Process attachment if provided
        attachment_path = None
        if attachment and attachment.filename:
            # Validate file type
            allowed_extensions = {'png', 'jpg', 'jpeg', 'pdf'}
            if '.' in attachment.filename and attachment.filename.rsplit('.', 1)[1].lower() in allowed_extensions:
                # Generate secure filename
                filename = secure_filename(f"{ticket_number}_{attachment.filename}")
                
                # Ensure directory exists
                upload_dir = os.path.join(Config.UPLOAD_FOLDER, 'support_attachments')
                os.makedirs(upload_dir, exist_ok=True)
                
                # Save file
                filepath = os.path.join(upload_dir, filename)
                attachment.save(filepath)
                
                attachment_path = filename
        
        # Create ticket
        ticket = SupportTicket(
            user_id=user_id,
            ticket_number=ticket_number,
            category=category,
            subject=subject,
            message=message,
            attachment_path=attachment_path
        )
        
        db.session.add(ticket)
        db.session.commit()
        
        # Send notification to admin (in a real app, you'd notify admins)
        # NotificationService.send_admin_notification("New support ticket", f"Ticket #{ticket_number} requires attention.")
        
        return True, "Support ticket created successfully.", ticket
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating support ticket: {str(e)}")
        return False, f"Error creating support ticket: {str(e)}", None

def get_user_tickets(user_id):
    """
    Get all tickets for a user.
    
    Args:
        user_id: User ID
    
    Returns:
        List of SupportTicket objects
    """
    return SupportTicket.query.filter_by(user_id=user_id).order_by(SupportTicket.created_at.desc()).all()

def get_ticket_by_number(ticket_number, user_id=None):
    """
    Get a ticket by number.
    
    Args:
        ticket_number: Ticket number
        user_id: Optional user ID for access control
    
    Returns:
        SupportTicket object or None
    """
    query = SupportTicket.query.filter_by(ticket_number=ticket_number)
    
    # If user_id is provided, ensure user can only access their own tickets
    if user_id:
        query = query.filter_by(user_id=user_id)
    
    return query.first()

def add_ticket_response(ticket_id, message, user_id=None, admin_id=None, attachment=None):
    """
    Add a response to a ticket.
    
    Args:
        ticket_id: Ticket ID
        message: Response message
        user_id: User ID (for user responses)
        admin_id: Admin ID (for admin responses)
        attachment: Optional file attachment
    
    Returns:
        Tuple of (success, message, response)
    """
    try:
        # Get ticket
        ticket = SupportTicket.query.get(ticket_id)
        if not ticket:
            return False, "Ticket not found.", None
        
        # Determine if this is an admin response
        is_admin_response = admin_id is not None
        
        # Process attachment if provided
        attachment_path = None
        if attachment and attachment.filename:
            # Validate file type
            allowed_extensions = {'png', 'jpg', 'jpeg', 'pdf'}
            if '.' in attachment.filename and attachment.filename.rsplit('.', 1)[1].lower() in allowed_extensions:
                # Generate secure filename
                response_id = str(random.randint(10000, 99999))
                filename = secure_filename(f"{ticket.ticket_number}_response_{response_id}_{attachment.filename}")
                
                # Ensure directory exists
                upload_dir = os.path.join(Config.UPLOAD_FOLDER, 'support_attachments')
                os.makedirs(upload_dir, exist_ok=True)
                
                # Save file
                filepath = os.path.join(upload_dir, filename)
                attachment.save(filepath)
                
                attachment_path = filename
        
        # Create response
        response = TicketResponse(
            ticket_id=ticket_id,
            user_id=user_id,
            admin_id=admin_id,
            message=message,
            attachment_path=attachment_path,
            is_admin_response=is_admin_response
        )
        
        db.session.add(response)
        
        # Update ticket status when admin responds
        if is_admin_response and ticket.status == 'open':
            ticket.status = 'in_progress'
        
        # Update ticket timestamp
        ticket.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Send notification
        if is_admin_response:
            # Notify user of admin response
            user = User.query.get(ticket.user_id)
            # In a real app, you would send an actual notification
            # NotificationService.send_email(user.email, "New response to your support ticket", f"Your ticket #{ticket.ticket_number} has received a response from support.")
        else:
            # Notify admin of user response (in a real app)
            pass
        
        return True, "Response added successfully.", response
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding ticket response: {str(e)}")
        return False, f"Error adding ticket response: {str(e)}", None

def update_ticket_status(ticket_id, status, admin_id):
    """
    Update a ticket's status.
    
    Args:
        ticket_id: Ticket ID
        status: New status ('open', 'in_progress', 'closed')
        admin_id: Admin ID
    
    Returns:
        Tuple of (success, message)
    """
    try:
        # Get ticket
        ticket = SupportTicket.query.get(ticket_id)
        if not ticket:
            return False, "Ticket not found."
        
        # Update status
        ticket.status = status
        ticket.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Add a system note about the status change
        admin = User.query.get(admin_id)
        admin_name = admin.username if admin else "Admin"
        
        status_message = f"Ticket status changed to {status} by {admin_name}."
        response = TicketResponse(
            ticket_id=ticket_id,
            admin_id=admin_id,
            message=status_message,
            is_admin_response=True
        )
        
        db.session.add(response)
        db.session.commit()
        
        # Notify user of status change (in a real app)
        user = User.query.get(ticket.user_id)
        # NotificationService.send_email(user.email, "Support ticket status updated", f"Your ticket #{ticket.ticket_number} status has been updated to {status}.")
        
        return True, f"Ticket status updated to {status}."
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating ticket status: {str(e)}")
        return False, f"Error updating ticket status: {str(e)}"

def update_ticket_priority(ticket_id, priority, admin_id):
    """
    Update a ticket's priority.
    
    Args:
        ticket_id: Ticket ID
        priority: New priority ('low', 'normal', 'high', 'urgent')
        admin_id: Admin ID
    
    Returns:
        Tuple of (success, message)
    """
    try:
        # Get ticket
        ticket = SupportTicket.query.get(ticket_id)
        if not ticket:
            return False, "Ticket not found."
        
        # Update priority
        old_priority = ticket.priority
        ticket.priority = priority
        ticket.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Add a system note about the priority change
        admin = User.query.get(admin_id)
        admin_name = admin.username if admin else "Admin"
        
        priority_message = f"Ticket priority changed from {old_priority} to {priority} by {admin_name}."
        response = TicketResponse(
            ticket_id=ticket_id,
            admin_id=admin_id,
            message=priority_message,
            is_admin_response=True
        )
        
        db.session.add(response)
        db.session.commit()
        
        return True, f"Ticket priority updated to {priority}."
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating ticket priority: {str(e)}")
        return False, f"Error updating ticket priority: {str(e)}"

def get_all_tickets(status=None, priority=None, page=1, per_page=20):
    """
    Get all tickets with optional filtering for admin view.
    
    Args:
        status: Optional status filter
        priority: Optional priority filter
        page: Page number
        per_page: Number of tickets per page
    
    Returns:
        Paginated query of SupportTicket objects
    """
    query = SupportTicket.query
    
    if status:
        query = query.filter_by(status=status)
    
    if priority:
        query = query.filter_by(priority=priority)
    
    # Order by priority first (urgent first), then by created date (oldest first)
    from sqlalchemy import case
    
    # Create the case expression correctly
    priority_case = case(
        (SupportTicket.priority == 'urgent', 0),
        (SupportTicket.priority == 'high', 1),
        (SupportTicket.priority == 'normal', 2),
        (SupportTicket.priority == 'low', 3),
        else_=4
    )
    
    # Use the case expression in order_by
    query = query.order_by(
        priority_case,
        SupportTicket.created_at.asc()
    )
    
    return query.paginate(page=page, per_page=per_page)

def get_ticket_details(ticket_id):
    """
    Get detailed information about a ticket including responses.
    
    Args:
        ticket_id: Ticket ID
    
    Returns:
        Dictionary with ticket details
    """
    ticket = SupportTicket.query.get(ticket_id)
    
    if not ticket:
        return None
    
    responses = TicketResponse.query.filter_by(ticket_id=ticket_id).order_by(TicketResponse.created_at.asc()).all()
    
    user = User.query.get(ticket.user_id)
    
    ticket_details = {
        'ticket': ticket,
        'user': user,
        'responses': responses
    }
    
    return ticket_details

def get_ticket_statistics():
    """
    Get statistics about support tickets for admin dashboard.
    
    Returns:
        Dictionary with ticket statistics
    """
    stats = {
        'total': SupportTicket.query.count(),
        'open': SupportTicket.query.filter_by(status='open').count(),
        'in_progress': SupportTicket.query.filter_by(status='in_progress').count(),
        'closed': SupportTicket.query.filter_by(status='closed').count(),
        'urgent': SupportTicket.query.filter_by(priority='urgent').count(),
        'high': SupportTicket.query.filter_by(priority='high').count(),
        'oldest_open': SupportTicket.query.filter_by(status='open').order_by(SupportTicket.created_at.asc()).first()
    }
    
    return stats