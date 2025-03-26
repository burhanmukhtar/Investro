# app/routes/admin_support.py
"""
Admin routes for support functionalities including ticket management and live chat support.
"""
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
from app.models.user import User
from app.models.chat import SupportTicket, TicketResponse, SupportChat, ChatMessage
from app.services.chat_service import get_waiting_chats_count, get_active_chats_count
from functools import wraps
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
admin_support = Blueprint('admin_support', __name__)

# Admin required decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Access denied. Admin privileges required.', 'danger')
            return redirect(url_for('user.home'))
        return f(*args, **kwargs)
    return decorated_function

@admin_support.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """Admin support dashboard with overview of tickets and chats"""
    try:
        # Get support stats
        open_tickets = SupportTicket.query.filter_by(status='open').count()
        in_progress_tickets = SupportTicket.query.filter_by(status='in_progress').count()
        waiting_chats = get_waiting_chats_count()
        active_chats = get_active_chats_count()
        
        # Get recent tickets
        recent_tickets = SupportTicket.query.order_by(SupportTicket.updated_at.desc()).limit(10).all()
        
        # Get waiting chats
        waiting_chat_list = SupportChat.query.filter_by(status='waiting').order_by(SupportChat.last_activity.desc()).limit(10).all()
        
        # Get active chats for this admin
        admin_active_chats = SupportChat.query.filter_by(admin_id=current_user.id, status='active').order_by(SupportChat.last_activity.desc()).all()
        
        return render_template('admin/support_dashboard.html', 
                              title='Support Dashboard',
                              open_tickets=open_tickets,
                              in_progress_tickets=in_progress_tickets,
                              waiting_chats=waiting_chats,
                              active_chats=active_chats,
                              recent_tickets=recent_tickets,
                              waiting_chat_list=waiting_chat_list,
                              admin_active_chats=admin_active_chats)
    except Exception as e:
        logger.error(f"Error loading admin support dashboard: {str(e)}")
        flash("Error loading support dashboard. Please try again later.", "danger")
        return redirect(url_for('admin.dashboard'))

@admin_support.route('/tickets')
@login_required
@admin_required
def tickets():
    """View all support tickets with filtering options"""
    try:
        # Get filter parameters
        status = request.args.get('status', 'all')
        assigned = request.args.get('assigned', 'all')
        page = request.args.get('page', 1, type=int)
        
        # Base query
        query = SupportTicket.query
        
        # Apply filters
        if status != 'all':
            query = query.filter_by(status=status)
            
        if assigned == 'me':
            query = query.filter_by(admin_id=current_user.id)
        elif assigned == 'unassigned':
            query = query.filter_by(admin_id=None)
        
        # Order by updated_at
        query = query.order_by(SupportTicket.updated_at.desc())
        
        # Paginate
        tickets = query.paginate(page=page, per_page=20)
        
        return render_template('admin/tickets.html', 
                              title='Support Tickets',
                              tickets=tickets,
                              status=status,
                              assigned=assigned)
    except Exception as e:
        logger.error(f"Error loading admin tickets view: {str(e)}")
        flash("Error loading tickets. Please try again later.", "danger")
        return redirect(url_for('admin_support.dashboard'))

@admin_support.route('/ticket/<int:ticket_id>')
@login_required
@admin_required
def view_ticket(ticket_id):
    """View a specific ticket with admin controls"""
    try:
        ticket = SupportTicket.query.get_or_404(ticket_id)
        
        # Get user details
        user = User.query.get(ticket.user_id)
        
        # Get ticket responses
        responses = TicketResponse.query.filter_by(ticket_id=ticket_id).order_by(TicketResponse.created_at.asc()).all()
        
        # Get associated chat if any
        chat = SupportChat.query.filter_by(ticket_id=ticket_id).first()
        
        return render_template('admin/ticket_detail.html', 
                              title=f'Ticket #{ticket.ticket_number}',
                              ticket=ticket,
                              user=user,
                              responses=responses,
                              chat=chat)
    except Exception as e:
        logger.error(f"Error viewing ticket {ticket_id}: {str(e)}")
        flash(f"Error viewing ticket: {str(e)}", "danger")
        return redirect(url_for('admin_support.tickets'))

@admin_support.route('/ticket/<int:ticket_id>/assign', methods=['POST'])
@login_required
@admin_required
def assign_ticket(ticket_id):
    """Assign a ticket to an admin"""
    try:
        ticket = SupportTicket.query.get_or_404(ticket_id)
        
        # Assign to the current admin
        ticket.admin_id = current_user.id
        
        # Update status if needed
        if ticket.status == 'open':
            ticket.status = 'in_progress'
            
        ticket.updated_at = datetime.utcnow()
        db.session.commit()
        
        flash(f'Ticket #{ticket.ticket_number} has been assigned to you.', 'success')
        return redirect(url_for('admin_support.view_ticket', ticket_id=ticket_id))
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error assigning ticket {ticket_id}: {str(e)}")
        flash(f"Error assigning ticket: {str(e)}", "danger")
        return redirect(url_for('admin_support.view_ticket', ticket_id=ticket_id))

@admin_support.route('/ticket/<int:ticket_id>/unassign', methods=['POST'])
@login_required
@admin_required
def unassign_ticket(ticket_id):
    """Unassign a ticket from an admin"""
    try:
        ticket = SupportTicket.query.get_or_404(ticket_id)
        
        # Unassign only if the current admin is assigned
        if ticket.admin_id == current_user.id or current_user.id == 1:  # Allow super admin to unassign any ticket
            ticket.admin_id = None
            
            # Update status if needed
            if ticket.status == 'in_progress':
                ticket.status = 'open'
                
            ticket.updated_at = datetime.utcnow()
            db.session.commit()
            
            flash(f'Ticket #{ticket.ticket_number} has been unassigned.', 'success')
        else:
            flash('You are not authorized to unassign this ticket.', 'danger')
            
        return redirect(url_for('admin_support.view_ticket', ticket_id=ticket_id))
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error unassigning ticket {ticket_id}: {str(e)}")
        flash(f"Error unassigning ticket: {str(e)}", "danger")
        return redirect(url_for('admin_support.view_ticket', ticket_id=ticket_id))

@admin_support.route('/ticket/<int:ticket_id>/update-status', methods=['POST'])
@login_required
@admin_required
def update_ticket_status(ticket_id):
    """Update a ticket's status"""
    try:
        ticket = SupportTicket.query.get_or_404(ticket_id)
        
        status = request.form.get('status')
        if not status or status not in ['open', 'in_progress', 'closed', 'reopened']:
            flash('Invalid status.', 'danger')
            return redirect(url_for('admin_support.view_ticket', ticket_id=ticket_id))
        
        ticket.status = status
        
        # If closing, update closed_at timestamp
        if status == 'closed':
            ticket.closed_at = datetime.utcnow()
        
        ticket.updated_at = datetime.utcnow()
        db.session.commit()
        
        flash(f'Ticket status updated to {status}.', 'success')
        return redirect(url_for('admin_support.view_ticket', ticket_id=ticket_id))
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating ticket status {ticket_id}: {str(e)}")
        flash(f"Error updating ticket status: {str(e)}", "danger")
        return redirect(url_for('admin_support.view_ticket', ticket_id=ticket_id))

@admin_support.route('/chats')
@login_required
@admin_required
def chats():
    """View all support chats with filtering options"""
    try:
        # Get filter parameters
        status = request.args.get('status', 'all')
        assigned = request.args.get('assigned', 'all')
        page = request.args.get('page', 1, type=int)
        
        # Base query
        query = SupportChat.query
        
        # Apply filters
        if status != 'all':
            query = query.filter_by(status=status)
            
        if assigned == 'me':
            query = query.filter_by(admin_id=current_user.id)
        elif assigned == 'unassigned':
            query = query.filter(
                (SupportChat.admin_id == None) &
                (SupportChat.status.in_(['new', 'waiting']))
            )
        
        # Order by last_activity
        query = query.order_by(SupportChat.last_activity.desc())
        
        # Paginate
        chats = query.paginate(page=page, per_page=20)
        
        return render_template('admin/chats.html', 
                              title='Support Chats',
                              chats=chats,
                              status=status,
                              assigned=assigned)
    except Exception as e:
        logger.error(f"Error loading admin chats view: {str(e)}")
        flash("Error loading chats. Please try again later.", "danger")
        return redirect(url_for('admin_support.dashboard'))

@admin_support.route('/chat/<int:chat_id>')
@login_required
@admin_required
def view_chat(chat_id):
    """View and join a specific chat session"""
    try:
        chat = SupportChat.query.get_or_404(chat_id)
        
        # Get user details
        user = User.query.get(chat.user_id)
        
        # Get associated ticket if any
        ticket = None
        if chat.ticket_id:
            ticket = SupportTicket.query.get(chat.ticket_id)
        
        # If no admin is assigned and chat is waiting, assign this admin
        if not chat.admin_id and chat.status in ['new', 'waiting']:
            chat.admin_id = current_user.id
            chat.status = 'active'
            db.session.commit()
            flash('You have been assigned to this chat.', 'info')
        
        return render_template('admin/chat_view.html', 
                              title='Support Chat',
                              chat=chat,
                              user=user,
                              ticket=ticket,
                              is_admin=True)
    except Exception as e:
        logger.error(f"Error viewing chat {chat_id}: {str(e)}")
        flash(f"Error viewing chat: {str(e)}", "danger")
        return redirect(url_for('admin_support.chats'))

@admin_support.route('/live-support')
@login_required
@admin_required
def live_support():
    """Live support console for handling multiple chats"""
    try:
        # Get all waiting chats
        waiting_chats = SupportChat.query.filter_by(status='waiting').order_by(SupportChat.last_activity.desc()).all()
        
        # Get active chats assigned to this admin
        active_chats = SupportChat.query.filter_by(admin_id=current_user.id, status='active').order_by(SupportChat.last_activity.desc()).all()
        
        return render_template('admin/live_support.html', 
                              title='Live Support Console',
                              waiting_chats=waiting_chats,
                              active_chats=active_chats)
    except Exception as e:
        logger.error(f"Error loading live support console: {str(e)}")
        flash("Error loading live support console. Please try again later.", "danger")
        return redirect(url_for('admin_support.dashboard'))

@admin_support.route('/api/chat-stats')
@login_required
@admin_required
def chat_stats():
    """Get current chat statistics for the admin dashboard"""
    try:
        # Get stats
        waiting_chats = get_waiting_chats_count()
        active_chats = get_active_chats_count()
        my_active_chats = SupportChat.query.filter_by(admin_id=current_user.id, status='active').count()
        
        # Get waiting chat list
        waiting_chat_list = SupportChat.query.filter_by(status='waiting').order_by(SupportChat.last_activity.desc()).limit(10).all()
        
        waiting_chats_data = []
        for chat in waiting_chat_list:
            user = User.query.get(chat.user_id)
            waiting_time = (datetime.utcnow() - chat.last_activity).total_seconds() // 60  # Minutes
            
            waiting_chats_data.append({
                'id': chat.id,
                'user_id': chat.user_id,
                'username': user.username if user else 'Unknown',
                'subject': chat.subject,
                'waiting_time': int(waiting_time),
                'created_at': chat.created_at.isoformat()
            })
        
        return jsonify({
            'success': True,
            'waiting_chats': waiting_chats,
            'active_chats': active_chats,
            'my_active_chats': my_active_chats,
            'waiting_list': waiting_chats_data
        })
    except Exception as e:
        logger.error(f"Error getting chat stats: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error getting chat stats: {str(e)}"
        }), 500

# app/routes/admin_support.py (continued)

@admin_support.route('/api/ticket-stats')
@login_required
@admin_required
def ticket_stats():
    """Get current ticket statistics for the admin dashboard"""
    try:
        # Get stats
        open_tickets = SupportTicket.query.filter_by(status='open').count()
        in_progress_tickets = SupportTicket.query.filter_by(status='in_progress').count()
        my_tickets = SupportTicket.query.filter_by(admin_id=current_user.id, status='in_progress').count()
        
        # Get recent updated tickets
        recent_tickets = SupportTicket.query.order_by(SupportTicket.updated_at.desc()).limit(10).all()
        
        recent_tickets_data = []
        for ticket in recent_tickets:
            user = User.query.get(ticket.user_id)
            
            recent_tickets_data.append({
                'id': ticket.id,
                'ticket_number': ticket.ticket_number,
                'user_id': ticket.user_id,
                'username': user.username if user else 'Unknown',
                'subject': ticket.subject,
                'category': ticket.category,
                'status': ticket.status,
                'admin_id': ticket.admin_id,
                'created_at': ticket.created_at.isoformat(),
                'updated_at': ticket.updated_at.isoformat()
            })
        
        return jsonify({
            'success': True,
            'open_tickets': open_tickets,
            'in_progress_tickets': in_progress_tickets,
            'my_tickets': my_tickets,
            'recent_tickets': recent_tickets_data
        })
    except Exception as e:
        logger.error(f"Error getting ticket stats: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error getting ticket stats: {str(e)}"
        }), 500

@admin_support.route('/api/support-overview')
@login_required
@admin_required
def support_overview():
    """Get a comprehensive overview of all support metrics"""
    try:
        # Ticket stats
        open_tickets = SupportTicket.query.filter_by(status='open').count()
        in_progress_tickets = SupportTicket.query.filter_by(status='in_progress').count()
        closed_tickets_today = SupportTicket.query.filter(
            SupportTicket.status == 'closed',
            SupportTicket.closed_at >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        ).count()
        
        # Chat stats
        waiting_chats = get_waiting_chats_count()
        active_chats = get_active_chats_count()
        closed_chats_today = SupportChat.query.filter(
            SupportChat.status == 'closed',
            SupportChat.closed_at >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        ).count()
        
        # Admin stats
        total_admins = User.query.filter_by(is_admin=True).count()
        online_admins = 0  # This would come from the chat service
        
        # Response times (average in minutes)
        # This requires more complex queries that would need optimization in a real system
        response_time = 0
        resolution_time = 0
        
        # Customer satisfaction
        avg_rating = db.session.query(db.func.avg(SupportChat.feedback_rating)).filter(
            SupportChat.feedback_rating.isnot(None)
        ).scalar() or 0
        
        return jsonify({
            'success': True,
            'tickets': {
                'open': open_tickets,
                'in_progress': in_progress_tickets,
                'closed_today': closed_tickets_today
            },
            'chats': {
                'waiting': waiting_chats,
                'active': active_chats,
                'closed_today': closed_chats_today
            },
            'admins': {
                'total': total_admins,
                'online': online_admins
            },
            'metrics': {
                'response_time': response_time,
                'resolution_time': resolution_time,
                'avg_rating': float(avg_rating)
            }
        })
    except Exception as e:
        logger.error(f"Error getting support overview: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error getting support overview: {str(e)}"
        }), 500

@admin_support.route('/api/chat/<int:chat_id>/join', methods=['POST'])
@login_required
@admin_required
def join_chat(chat_id):
    """Join a chat as an admin"""
    try:
        chat = SupportChat.query.get_or_404(chat_id)
        
        # Check if the chat is already assigned to another admin
        if chat.admin_id and chat.admin_id != current_user.id:
            admin = User.query.get(chat.admin_id)
            return jsonify({
                'success': False,
                'message': f'This chat is already assigned to {admin.username if admin else "another admin"}'
            }), 400
        
        # Assign this admin if not already assigned
        if not chat.admin_id:
            chat.admin_id = current_user.id
        
        # Update chat status to active if it's new or waiting
        if chat.status in ['new', 'waiting']:
            chat.status = 'active'
            
        chat.last_activity = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'You have joined the chat'
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error joining chat {chat_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error joining chat: {str(e)}"
        }), 500

@admin_support.route('/api/chat/<int:chat_id>/leave', methods=['POST'])
@login_required
@admin_required
def leave_chat(chat_id):
    """Leave a chat as an admin"""
    try:
        chat = SupportChat.query.get_or_404(chat_id)
        
        # Only allow leaving if this admin is assigned
        if chat.admin_id != current_user.id:
            return jsonify({
                'success': False,
                'message': 'You are not assigned to this chat'
            }), 400
        
        # Clear admin assignment
        chat.admin_id = None
        
        # Update chat status to waiting if it was active
        if chat.status == 'active':
            chat.status = 'waiting'
            
        chat.last_activity = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'You have left the chat'
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error leaving chat {chat_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error leaving chat: {str(e)}"
        }), 500

@admin_support.route('/api/chat/<int:chat_id>/transfer', methods=['POST'])
@login_required
@admin_required
def transfer_chat(chat_id):
    """Transfer a chat to another admin"""
    try:
        chat = SupportChat.query.get_or_404(chat_id)
        
        # Only allow transferring if this admin is assigned
        if chat.admin_id != current_user.id and current_user.id != 1:  # Allow super admin to transfer any chat
            return jsonify({
                'success': False,
                'message': 'You are not authorized to transfer this chat'
            }), 400
        
        # Get the target admin ID
        data = request.get_json()
        admin_id = data.get('admin_id')
        
        if not admin_id:
            return jsonify({
                'success': False,
                'message': 'Target admin ID is required'
            }), 400
        
        # Verify the target admin exists
        admin = User.query.get(admin_id)
        if not admin or not admin.is_admin:
            return jsonify({
                'success': False,
                'message': 'Invalid target admin'
            }), 400
        
        # Transfer the chat
        chat.admin_id = admin_id
        chat.last_activity = datetime.utcnow()
        
        # Create a system message indicating the transfer
        system_message = ChatMessage(
            chat_id=chat_id,
            sender_id=current_user.id,
            sender_name="System",
            is_admin=True,
            content=f"Chat transferred to {admin.username}"
        )
        
        db.session.add(system_message)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Chat transferred to {admin.username}'
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error transferring chat {chat_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error transferring chat: {str(e)}"
        }), 500

@admin_support.route('/api/register-support-agent', methods=['POST'])
@login_required
@admin_required
def register_support_agent():
    """Register current admin as available for live support"""
    try:
        # This function sets up a WebSocket connection with the admin
        # The actual registration is handled by the socket.io event handler
        
        return jsonify({
            'success': True,
            'message': 'Support agent registration initialized'
        })
    except Exception as e:
        logger.error(f"Error registering support agent: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error registering support agent: {str(e)}"
        }), 500

@admin_support.route('/api/unregister-support-agent', methods=['POST'])
@login_required
@admin_required
def unregister_support_agent():
    """Unregister current admin from live support"""
    try:
        # This function tells the system the admin is no longer available
        # The actual unregistration is handled by the socket.io event handler
        
        return jsonify({
            'success': True,
            'message': 'Support agent unregistered'
        })
    except Exception as e:
        logger.error(f"Error unregistering support agent: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error unregistering support agent: {str(e)}"
        }), 500

@admin_support.route('/api/canned-responses')
@login_required
@admin_required
def get_canned_responses():
    """Get a list of canned responses for quick replies"""
    try:
        # In a real implementation, these would come from a database
        # For now, we'll return a static list
        canned_responses = [
            {
                'id': 1,
                'title': 'Greeting',
                'content': 'Hello! Thank you for contacting support. How can I help you today?'
            },
            {
                'id': 2,
                'title': 'Request More Info',
                'content': 'Could you please provide more details about the issue you\'re experiencing?'
            },
            {
                'id': 3,
                'title': 'Verification Required',
                'content': 'For security reasons, we need to verify your identity. Please complete the verification process in your profile settings.'
            },
            {
                'id': 4,
                'title': 'Closing Chat',
                'content': 'Is there anything else I can help you with today?'
            },
            {
                'id': 5,
                'title': 'Thank You',
                'content': 'Thank you for contacting support. Have a great day!'
            }
        ]
        
        return jsonify({
            'success': True,
            'canned_responses': canned_responses
        })
    except Exception as e:
        logger.error(f"Error getting canned responses: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error getting canned responses: {str(e)}"
        }), 500

@admin_support.route('/api/user-info/<int:user_id>')
@login_required
@admin_required
def get_user_info(user_id):
    """Get detailed information about a user for support purposes"""
    try:
        user = User.query.get_or_404(user_id)
        
        # Get user's tickets
        tickets = SupportTicket.query.filter_by(user_id=user_id).order_by(SupportTicket.created_at.desc()).limit(5).all()
        
        tickets_data = [{
            'id': ticket.id,
            'ticket_number': ticket.ticket_number,
            'subject': ticket.subject,
            'status': ticket.status,
            'created_at': ticket.created_at.isoformat()
        } for ticket in tickets]
        
        # Get user's wallet balances
        from app.models.wallet import Wallet
        wallets = Wallet.query.filter_by(user_id=user_id).all()
        
        wallets_data = [{
            'currency': wallet.currency,
            'spot_balance': wallet.spot_balance,
            'funding_balance': wallet.funding_balance,
            'futures_balance': wallet.futures_balance
        } for wallet in wallets]
        
        # Get user's verification status
        verification_status = user.verification_status
        is_verified = user.is_verified
        
        return jsonify({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'phone': user.phone,
                'unique_id': user.unique_id,
                'verification_status': verification_status,
                'is_verified': is_verified,
                'created_at': user.created_at.isoformat()
            },
            'tickets': tickets_data,
            'wallets': wallets_data
        })
    except Exception as e:
        logger.error(f"Error getting user info {user_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error getting user info: {str(e)}"
        }), 500

@admin_support.route('/api/chat-history/<int:chat_id>')
@login_required
@admin_required
def get_chat_history(chat_id):
    """Get chat history with detailed user context"""
    try:
        chat = SupportChat.query.get_or_404(chat_id)
        
        # Make sure admin has access to this chat
        if chat.admin_id != current_user.id and current_user.id != 1:  # Allow super admin to view any chat
            return jsonify({
                'success': False,
                'message': 'You are not authorized to view this chat'
            }), 403
        
        # Get user details
        user = User.query.get(chat.user_id)
        
        # Get chat messages
        messages = ChatMessage.query.filter_by(chat_id=chat_id).order_by(ChatMessage.timestamp.asc()).all()
        
        messages_data = [{
            'id': msg.id,
            'sender_id': msg.sender_id,
            'sender_name': msg.sender_name,
            'is_admin': msg.is_admin,
            'content': msg.content,
            'timestamp': msg.timestamp.isoformat(),
            'read': msg.read
        } for msg in messages]
        
        # Get associated ticket if any
        ticket = None
        if chat.ticket_id:
            ticket = SupportTicket.query.get(chat.ticket_id)
            
            if ticket:
                ticket = {
                    'id': ticket.id,
                    'ticket_number': ticket.ticket_number,
                    'subject': ticket.subject,
                    'status': ticket.status
                }
        
        return jsonify({
            'success': True,
            'chat': {
                'id': chat.id,
                'subject': chat.subject,
                'status': chat.status,
                'created_at': chat.created_at.isoformat(),
                'last_activity': chat.last_activity.isoformat()
            },
            'user': {
                'id': user.id,
                'username': user.username,
                'is_verified': user.is_verified
            } if user else None,
            'messages': messages_data,
            'ticket': ticket
        })
    except Exception as e:
        logger.error(f"Error getting chat history {chat_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error getting chat history: {str(e)}"
        }), 500