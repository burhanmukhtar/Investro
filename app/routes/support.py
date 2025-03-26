# app/routes/support.py
"""
Routes for support functionality including tickets and chat.
Used by regular users to contact support.
"""
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.models.user import User
from app.models.chat import SupportTicket, TicketResponse, SupportChat, ChatMessage
from app.services.chat_service import is_support_available
import os
import uuid
from datetime import datetime
import logging
import random
import string

logger = logging.getLogger(__name__)
support = Blueprint('support', __name__)

def generate_ticket_number():
    """Generate a unique ticket number"""
    prefix = ''.join(random.choices(string.ascii_uppercase, k=2))
    number = ''.join(random.choices(string.digits, k=6))
    return f"{prefix}{number}"

@support.route('/')
@login_required
def index():
    """Support main page with ticket history and chat option"""
    try:
        # Get user's tickets
        tickets = SupportTicket.query.filter_by(user_id=current_user.id).order_by(SupportTicket.created_at.desc()).all()
        
        # Get user's active chats
        active_chats = SupportChat.query.filter_by(
            user_id=current_user.id,
            status='active'
        ).order_by(SupportChat.last_activity.desc()).all()
        
        # Check if support is available
        support_available = is_support_available()
        
        return render_template('user/support.html', 
                              title='Support Center',
                              tickets=tickets,
                              active_chats=active_chats,
                              support_available=support_available)
    except Exception as e:
        logger.error(f"Error loading support page: {str(e)}")
        flash("Error loading support page. Please try again later.", "danger")
        return redirect(url_for('user.home'))

@support.route('/ticket/create', methods=['POST'])
@login_required
def create_ticket():
    """Create a new support ticket"""
    try:
        subject = request.form.get('subject')
        category = request.form.get('category')
        message = request.form.get('message')
        
        if not subject or not category or not message:
            flash('All fields are required.', 'danger')
            return redirect(url_for('support.index'))
        
        # Generate a unique ticket number
        ticket_number = generate_ticket_number()
        while SupportTicket.query.filter_by(ticket_number=ticket_number).first():
            ticket_number = generate_ticket_number()
        
        # Create the ticket
        ticket = SupportTicket(
            ticket_number=ticket_number,
            user_id=current_user.id,
            subject=subject,
            category=category,
            message=message
        )
        
        # Handle attachment if provided
        if 'attachment' in request.files:
            file = request.files['attachment']
            if file and file.filename:
                # Save attachment
                filename = secure_filename(f"{ticket_number}_{file.filename}")
                upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'support_attachments')
                os.makedirs(upload_dir, exist_ok=True)
                filepath = os.path.join(upload_dir, filename)
                file.save(filepath)
                ticket.attachment_path = filename
        
        db.session.add(ticket)
        db.session.commit()
        
        flash('Your ticket has been submitted successfully!', 'success')
        return redirect(url_for('support.view_ticket', ticket_id=ticket.id))
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating ticket: {str(e)}")
        flash(f"Error creating ticket: {str(e)}", "danger")
        return redirect(url_for('support.index'))

# app/routes/support.py (continued)

@support.route('/ticket/<int:ticket_id>')
@login_required
def view_ticket(ticket_id):
    """View a specific support ticket"""
    try:
        # Ensure the ticket belongs to the current user or user is admin
        ticket = SupportTicket.query.get_or_404(ticket_id)
        if ticket.user_id != current_user.id and not current_user.is_admin:
            flash('You do not have permission to view this ticket.', 'danger')
            return redirect(url_for('support.index'))
        
        # Get ticket responses
        responses = TicketResponse.query.filter_by(ticket_id=ticket_id).order_by(TicketResponse.created_at.asc()).all()
        
        # Get associated chat if any
        chat = SupportChat.query.filter_by(ticket_id=ticket_id).first()
        
        return render_template('user/ticket_detail.html', 
                              title=f'Ticket #{ticket.ticket_number}',
                              ticket=ticket,
                              responses=responses,
                              chat=chat)
    except Exception as e:
        logger.error(f"Error viewing ticket {ticket_id}: {str(e)}")
        flash(f"Error viewing ticket: {str(e)}", "danger")
        return redirect(url_for('support.index'))

@support.route('/ticket/<int:ticket_id>/reply', methods=['POST'])
@login_required
def reply_to_ticket(ticket_id):
    """Reply to an existing support ticket"""
    try:
        ticket = SupportTicket.query.get_or_404(ticket_id)
        
        # Ensure the ticket belongs to the current user or user is admin
        if ticket.user_id != current_user.id and not current_user.is_admin:
            flash('You do not have permission to reply to this ticket.', 'danger')
            return redirect(url_for('support.index'))
        
        message = request.form.get('message')
        
        if not message:
            flash('Message cannot be empty.', 'danger')
            return redirect(url_for('support.view_ticket', ticket_id=ticket_id))
        
        # Create the response
        response = TicketResponse(
            ticket_id=ticket_id,
            responder_id=current_user.id,
            message=message,
            is_admin=current_user.is_admin
        )
        
        # Handle attachment if provided
        if 'attachment' in request.files:
            file = request.files['attachment']
            if file and file.filename:
                # Save attachment
                filename = secure_filename(f"{ticket.ticket_number}_response_{response.id}_{file.filename}")
                upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'support_attachments')
                os.makedirs(upload_dir, exist_ok=True)
                filepath = os.path.join(upload_dir, filename)
                file.save(filepath)
                response.attachment_path = filename
        
        # Update ticket status
        if ticket.status == 'closed':
            ticket.status = 'reopened'
        elif ticket.status == 'open' and current_user.is_admin:
            ticket.status = 'in_progress'
        
        ticket.updated_at = datetime.utcnow()
        
        # If admin is responding and no admin is assigned, assign this admin
        if current_user.is_admin and not ticket.admin_id:
            ticket.admin_id = current_user.id
        
        db.session.add(response)
        db.session.commit()
        
        flash('Your response has been submitted.', 'success')
        return redirect(url_for('support.view_ticket', ticket_id=ticket_id))
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error replying to ticket {ticket_id}: {str(e)}")
        flash(f"Error submitting response: {str(e)}", "danger")
        return redirect(url_for('support.view_ticket', ticket_id=ticket_id))

@support.route('/ticket/<int:ticket_id>/close', methods=['POST'])
@login_required
def close_ticket(ticket_id):
    """Close a support ticket"""
    try:
        ticket = SupportTicket.query.get_or_404(ticket_id)
        
        # Ensure the ticket belongs to the current user or user is admin
        if ticket.user_id != current_user.id and not current_user.is_admin:
            flash('You do not have permission to close this ticket.', 'danger')
            return redirect(url_for('support.index'))
        
        # Update ticket status
        ticket.status = 'closed'
        ticket.closed_at = datetime.utcnow()
        db.session.commit()
        
        flash('Ticket has been closed.', 'success')
        return redirect(url_for('support.view_ticket', ticket_id=ticket_id))
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error closing ticket {ticket_id}: {str(e)}")
        flash(f"Error closing ticket: {str(e)}", "danger")
        return redirect(url_for('support.view_ticket', ticket_id=ticket_id))

@support.route('/chat/start', methods=['POST'])
@login_required
def start_chat():
    """Start a new support chat"""
    try:
        # Check if support is available
        if not is_support_available():
            flash('Live support is currently unavailable. Please submit a ticket instead.', 'warning')
            return redirect(url_for('support.index'))
        
        subject = request.form.get('subject')
        
        if not subject:
            subject = 'General Support'
        
        # Create a new chat
        chat = SupportChat(
            user_id=current_user.id,
            subject=subject,
            status='new'
        )
        
        # Optional: Associate with a ticket if coming from ticket
        ticket_id = request.form.get('ticket_id')
        if ticket_id:
            ticket = SupportTicket.query.get(ticket_id)
            if ticket and (ticket.user_id == current_user.id or current_user.is_admin):
                chat.ticket_id = ticket_id
                chat.subject = f"Ticket #{ticket.ticket_number}: {ticket.subject}"
        
        db.session.add(chat)
        db.session.commit()
        
        # Redirect to chat interface
        return redirect(url_for('support.chat', chat_id=chat.id))
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error starting chat: {str(e)}")
        flash(f"Error starting chat: {str(e)}", "danger")
        return redirect(url_for('support.index'))

@support.route('/chat/<int:chat_id>')
@login_required
def chat(chat_id):
    """View and participate in a support chat"""
    try:
        # Ensure the chat belongs to the current user or user is admin
        chat = SupportChat.query.get_or_404(chat_id)
        if chat.user_id != current_user.id and not current_user.is_admin:
            flash('You do not have permission to view this chat.', 'danger')
            return redirect(url_for('support.index'))
        
        # Get associated ticket if any
        ticket = None
        if chat.ticket_id:
            ticket = SupportTicket.query.get(chat.ticket_id)
        
        # Get user and admin details
        user = User.query.get(chat.user_id)
        admin = None
        if chat.admin_id:
            admin = User.query.get(chat.admin_id)
        
        return render_template('user/chat.html', 
                              title='Support Chat',
                              chat=chat,
                              ticket=ticket,
                              user=user,
                              admin=admin,
                              is_admin=current_user.is_admin)
    except Exception as e:
        logger.error(f"Error viewing chat {chat_id}: {str(e)}")
        flash(f"Error viewing chat: {str(e)}", "danger")
        return redirect(url_for('support.index'))

@support.route('/chat/<int:chat_id>/close', methods=['POST'])
@login_required
def close_chat(chat_id):
    """Close a support chat"""
    try:
        chat = SupportChat.query.get_or_404(chat_id)
        
        # Ensure the chat belongs to the current user or user is admin
        if chat.user_id != current_user.id and not current_user.is_admin:
            flash('You do not have permission to close this chat.', 'danger')
            return redirect(url_for('support.index'))
        
        # Update chat status
        chat.status = 'closed'
        chat.closed_at = datetime.utcnow()
        
        # If closing from user side, request feedback
        feedback_rating = request.form.get('rating')
        feedback_comment = request.form.get('comment')
        
        if feedback_rating:
            try:
                chat.feedback_rating = int(feedback_rating)
                chat.feedback_comment = feedback_comment
            except ValueError:
                pass
        
        db.session.commit()
        
        flash('Chat has been closed.', 'success')
        return redirect(url_for('support.index'))
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error closing chat {chat_id}: {str(e)}")
        flash(f"Error closing chat: {str(e)}", "danger")
        return redirect(url_for('support.chat', chat_id=chat_id))

@support.route('/api/chat/<int:chat_id>/messages')
@login_required
def get_chat_messages(chat_id):
    """API endpoint to get chat messages"""
    try:
        # Ensure the chat belongs to the current user or user is admin
        chat = SupportChat.query.get_or_404(chat_id)
        if chat.user_id != current_user.id and not current_user.is_admin:
            return jsonify({
                'success': False,
                'message': 'Unauthorized access'
            }), 403
        
        # Get messages
        messages = ChatMessage.query.filter_by(chat_id=chat_id).order_by(ChatMessage.timestamp.asc()).all()
        
        # Format messages for response
        formatted_messages = []
        for msg in messages:
            formatted_messages.append({
                'id': msg.id,
                'sender_id': msg.sender_id,
                'sender_name': msg.sender_name,
                'is_admin': msg.is_admin,
                'content': msg.content,
                'timestamp': msg.timestamp.isoformat(),
                'read': msg.read
            })
            
            # Mark messages as read if they're from the other party
            if (current_user.is_admin and not msg.is_admin and not msg.read) or \
               (not current_user.is_admin and msg.is_admin and not msg.read):
                msg.read = True
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'messages': formatted_messages
        })
    except Exception as e:
        logger.error(f"Error getting chat messages {chat_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error getting messages: {str(e)}"
        }), 500

@support.route('/api/chat/<int:chat_id>/send', methods=['POST'])
@login_required
def send_chat_message(chat_id):
    """API endpoint to send a chat message"""
    try:
        # Ensure the chat belongs to the current user or user is admin
        chat = SupportChat.query.get_or_404(chat_id)
        if chat.user_id != current_user.id and not current_user.is_admin:
            return jsonify({
                'success': False,
                'message': 'Unauthorized access'
            }), 403
        
        # Check if chat is active
        if chat.status not in ['new', 'waiting', 'active']:
            return jsonify({
                'success': False,
                'message': 'This chat is closed.'
            }), 400
        
        # Get message content
        data = request.get_json()
        content = data.get('content')
        
        if not content:
            return jsonify({
                'success': False,
                'message': 'Message content is required.'
            }), 400
        
        # Create message
        message = ChatMessage(
            chat_id=chat_id,
            sender_id=current_user.id,
            sender_name=current_user.username,
            is_admin=current_user.is_admin,
            content=content
        )
        
        # Update chat status and last activity
        chat.last_activity = datetime.utcnow()
        
        if chat.status == 'new' and not current_user.is_admin:
            chat.status = 'waiting'
        elif chat.status in ['new', 'waiting'] and current_user.is_admin:
            chat.status = 'active'
            # Assign admin if not already assigned
            if not chat.admin_id:
                chat.admin_id = current_user.id
        
        db.session.add(message)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': {
                'id': message.id,
                'sender_id': message.sender_id,
                'sender_name': message.sender_name,
                'is_admin': message.is_admin,
                'content': message.content,
                'timestamp': message.timestamp.isoformat(),
                'read': message.read
            }
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error sending chat message {chat_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error sending message: {str(e)}"
        }), 500

@support.route('/api/support-status')
@login_required
def support_status():
    """API endpoint to check if support is available"""
    try:
        available = is_support_available()
        
        return jsonify({
            'success': True,
            'available': available
        })
    except Exception as e:
        logger.error(f"Error checking support status: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error checking support status: {str(e)}"
        }), 500