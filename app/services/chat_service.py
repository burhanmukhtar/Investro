# app/services/chat_service.py
"""
Chat service implementation using WebSockets.
Handles real-time communication between users and support staff.
"""
import json
import logging
from datetime import datetime
from flask_socketio import SocketIO, emit, join_room, leave_room
from app import db
from app.models.chat import SupportChat, ChatMessage
from app.models.user import User
import requests
logger = logging.getLogger(__name__)

# Initialize SocketIO instance (to be integrated with the Flask app)
socketio = SocketIO()

# Active support chats
active_chats = {}
# Admin support staff availability status
support_staff = {}

@socketio.on('connect')
def handle_connect():
    """Handle client connection to WebSocket"""
    try:
        logger.info(f"Client connected: {request.sid}")
    except Exception as e:
        logger.error(f"Error in connect handler: {str(e)}")

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection from WebSocket"""
    try:
        logger.info(f"Client disconnected: {request.sid}")
        
        # Check if this was an admin user
        for admin_id, data in support_staff.items():
            if data.get('sid') == request.sid:
                support_staff[admin_id]['online'] = False
                support_staff[admin_id]['sid'] = None
                # Broadcast admin status update to all
                emit('support_status_update', 
                     {'admin_id': admin_id, 'online': False}, 
                     broadcast=True)
                break
    except Exception as e:
        logger.error(f"Error in disconnect handler: {str(e)}")

@socketio.on('join_chat')
def handle_join_chat(data):
    """
    Handle a user or admin joining a chat room
    
    Args:
        data: Dict containing chat_id and user info
    """
    try:
        chat_id = data.get('chat_id')
        user_id = data.get('user_id')
        is_admin = data.get('is_admin', False)
        
        if not chat_id or not user_id:
            emit('error', {'message': 'Missing required parameters'})
            return
            
        # Join the room
        join_room(chat_id)
        
        # Update active chats tracking
        if chat_id not in active_chats:
            active_chats[chat_id] = {
                'user_id': None,
                'admin_id': None,
                'user_sid': None,
                'admin_sid': None,
                'last_activity': datetime.utcnow()
            }
        
        # Update specific fields based on who joined
        if is_admin:
            active_chats[chat_id]['admin_id'] = user_id
            active_chats[chat_id]['admin_sid'] = request.sid
            
            # Update admin's status in support_staff
            if user_id in support_staff:
                support_staff[user_id]['online'] = True
                support_staff[user_id]['sid'] = request.sid
                support_staff[user_id]['chats'] = support_staff[user_id].get('chats', [])
                if chat_id not in support_staff[user_id]['chats']:
                    support_staff[user_id]['chats'].append(chat_id)
            else:
                support_staff[user_id] = {
                    'online': True,
                    'sid': request.sid,
                    'chats': [chat_id]
                }
                
            # Get admin details to send to user
            admin = User.query.get(user_id)
            if admin:
                # Notify the chat room that admin joined
                emit('admin_joined', {
                    'admin_id': user_id,
                    'admin_name': admin.username,
                    'timestamp': datetime.utcnow().isoformat()
                }, room=chat_id)
        else:
            active_chats[chat_id]['user_id'] = user_id
            active_chats[chat_id]['user_sid'] = request.sid
            
            # Notify the chat room that user joined
            user = User.query.get(user_id)
            if user:
                emit('user_joined', {
                    'user_id': user_id,
                    'user_name': user.username,
                    'timestamp': datetime.utcnow().isoformat()
                }, room=chat_id)
        
        # Load and send chat history
        chat = SupportChat.query.get(chat_id)
        if chat:
            messages = ChatMessage.query.filter_by(chat_id=chat_id).order_by(ChatMessage.timestamp.asc()).all()
            
            history = [{
                'id': msg.id,
                'sender_id': msg.sender_id,
                'sender_name': msg.sender_name,
                'is_admin': msg.is_admin,
                'content': msg.content,
                'timestamp': msg.timestamp.isoformat(),
                'read': msg.read
            } for msg in messages]
            
            emit('chat_history', {
                'chat_id': chat_id,
                'history': history
            })
            
            # If a user is joining, mark all admin messages as read
            if not is_admin:
                for msg in messages:
                    if msg.is_admin and not msg.read:
                        msg.read = True
                db.session.commit()
                
            # If an admin is joining, update the chat status if needed
            if is_admin and chat.status == 'waiting':
                chat.status = 'active'
                db.session.commit()
                
                # Notify user that an admin has joined
                emit('chat_status_update', {
                    'chat_id': chat_id,
                    'status': 'active',
                    'message': 'Support agent has joined the chat'
                }, room=chat_id)
    except Exception as e:
        logger.error(f"Error in join_chat handler: {str(e)}")
        emit('error', {'message': 'An error occurred while joining the chat'})

@socketio.on('leave_chat')
def handle_leave_chat(data):
    """
    Handle a user or admin leaving a chat room
    
    Args:
        data: Dict containing chat_id and user info
    """
    try:
        chat_id = data.get('chat_id')
        user_id = data.get('user_id')
        is_admin = data.get('is_admin', False)
        
        if not chat_id:
            emit('error', {'message': 'Missing chat_id parameter'})
            return
            
        # Leave the room
        leave_room(chat_id)
        
        # Update active chats tracking
        if chat_id in active_chats:
            if is_admin:
                active_chats[chat_id]['admin_id'] = None
                active_chats[chat_id]['admin_sid'] = None
                
                # Update admin's status
                if user_id in support_staff and chat_id in support_staff[user_id].get('chats', []):
                    support_staff[user_id]['chats'].remove(chat_id)
                
                # Notify the chat room that admin left
                emit('admin_left', {
                    'admin_id': user_id,
                    'timestamp': datetime.utcnow().isoformat()
                }, room=chat_id)
            else:
                active_chats[chat_id]['user_id'] = None
                active_chats[chat_id]['user_sid'] = None
                
                # Notify the chat room that user left
                emit('user_left', {
                    'user_id': user_id,
                    'timestamp': datetime.utcnow().isoformat()
                }, room=chat_id)
            
            # Clean up if both parties have left
            if active_chats[chat_id]['user_id'] is None and active_chats[chat_id]['admin_id'] is None:
                del active_chats[chat_id]
    except Exception as e:
        logger.error(f"Error in leave_chat handler: {str(e)}")
        emit('error', {'message': 'An error occurred while leaving the chat'})

@socketio.on('send_message')
def handle_send_message(data):
    """
    Handle sending a message in a chat
    
    Args:
        data: Dict containing chat_id, sender info, and message content
    """
    try:
        chat_id = data.get('chat_id')
        sender_id = data.get('sender_id')
        content = data.get('content')
        is_admin = data.get('is_admin', False)
        
        if not chat_id or not sender_id or not content:
            emit('error', {'message': 'Missing required parameters'})
            return
            
        # Get sender details
        sender = User.query.get(sender_id)
        if not sender:
            emit('error', {'message': 'Sender not found'})
            return
        
        # Create and save message
        message = ChatMessage(
            chat_id=chat_id,
            sender_id=sender_id,
            sender_name=sender.username,
            is_admin=is_admin,
            content=content,
            # Admin messages are marked as read if user is active in chat
            # User messages are always unread until admin sees them
            read=is_admin and active_chats.get(chat_id, {}).get('user_sid') is not None
        )
        
        db.session.add(message)
        db.session.commit()
        
        # Update chat's last activity timestamp
        chat = SupportChat.query.get(chat_id)
        if chat:
            chat.last_activity = datetime.utcnow()
            
            # If first user message, update status from 'new' to 'waiting'
            if chat.status == 'new' and not is_admin:
                chat.status = 'waiting'
            
            db.session.commit()
            
        # Broadcast the message to the room
        emit('new_message', {
            'id': message.id,
            'chat_id': chat_id,
            'sender_id': sender_id,
            'sender_name': sender.username,
            'is_admin': is_admin,
            'content': content,
            'timestamp': message.timestamp.isoformat(),
            'read': message.read
        }, room=chat_id)
        
        # If user is sending, also notify all available support staff
        if not is_admin:
            # If no admin is assigned to this chat, notify available admins
            if not active_chats.get(chat_id, {}).get('admin_id'):
                notify_admin_staff_new_message(chat_id, sender.username, content)
    except Exception as e:
        logger.error(f"Error in send_message handler: {str(e)}")
        emit('error', {'message': 'An error occurred while sending the message'})

def notify_admin_staff_new_message(chat_id, username, content_preview):
    """Notify all available admin staff about a new message"""
    try:
        # Find available admin staff
        for admin_id, data in support_staff.items():
            if data.get('online', False) and data.get('sid'):
                # Don't notify if admin is already in this chat
                if chat_id in data.get('chats', []):
                    continue
                    
                # Send notification to this admin
                emit('new_chat_notification', {
                    'chat_id': chat_id,
                    'username': username,
                    'content_preview': content_preview[:50] + ('...' if len(content_preview) > 50 else ''),
                    'timestamp': datetime.utcnow().isoformat()
                }, room=data['sid'])
    except Exception as e:
        logger.error(f"Error notifying admin staff: {str(e)}")

@socketio.on('admin_register')
def handle_admin_register(data):
    """
    Register an admin as available for support
    
    Args:
        data: Dict containing admin_id
    """
    try:
        admin_id = data.get('admin_id')
        if not admin_id:
            emit('error', {'message': 'Missing admin_id parameter'})
            return
            
        # Verify this is actually an admin
        admin = User.query.get(admin_id)
        if not admin or not admin.is_admin:
            emit('error', {'message': 'Unauthorized'})
            return
            
        # Register admin as available
        support_staff[admin_id] = {
            'online': True,
            'sid': request.sid,
            'chats': []
        }
        
        logger.info(f"Admin {admin_id} registered for support")
        
        # Notify this admin about waiting chats
        waiting_chats = SupportChat.query.filter_by(status='waiting').order_by(SupportChat.last_activity.desc()).limit(10).all()
        
        waiting_chat_data = [{
            'id': chat.id,
            'user_id': chat.user_id,
            'username': User.query.get(chat.user_id).username if User.query.get(chat.user_id) else 'Unknown',
            'subject': chat.subject,
            'status': chat.status,
            'created_at': chat.created_at.isoformat(),
            'last_activity': chat.last_activity.isoformat() if chat.last_activity else chat.created_at.isoformat()
        } for chat in waiting_chats]
        
        emit('waiting_chats_update', {
            'waiting_chats': waiting_chat_data
        })
        
        # Broadcast admin status update to all users
        emit('support_status_update', 
             {'admin_id': admin_id, 'online': True}, 
             broadcast=True)
    except Exception as e:
        logger.error(f"Error in admin_register handler: {str(e)}")
        emit('error', {'message': 'An error occurred during registration'})

@socketio.on('admin_deregister')
def handle_admin_deregister(data):
    """
    Deregister an admin from being available for support
    
    Args:
        data: Dict containing admin_id
    """
    try:
        admin_id = data.get('admin_id')
        if not admin_id:
            emit('error', {'message': 'Missing admin_id parameter'})
            return
            
        # Remove admin from available support staff
        if admin_id in support_staff:
            support_staff[admin_id]['online'] = False
            
            # Notify clients in their active chats
            for chat_id in support_staff[admin_id].get('chats', []):
                emit('admin_left', {
                    'admin_id': admin_id,
                    'reason': 'offline',
                    'timestamp': datetime.utcnow().isoformat()
                }, room=chat_id)
            
            # Broadcast admin status update to all users
            emit('support_status_update', 
                 {'admin_id': admin_id, 'online': False}, 
                 broadcast=True)
            
            logger.info(f"Admin {admin_id} deregistered from support")
    except Exception as e:
        logger.error(f"Error in admin_deregister handler: {str(e)}")
        emit('error', {'message': 'An error occurred during deregistration'})

@socketio.on('mark_messages_read')
def handle_mark_messages_read(data):
    """
    Mark messages as read
    
    Args:
        data: Dict containing chat_id and last_read_id
    """
    try:
        chat_id = data.get('chat_id')
        user_id = data.get('user_id')
        is_admin = data.get('is_admin', False)
        last_read_id = data.get('last_read_id')
        
        if not chat_id or not user_id:
            emit('error', {'message': 'Missing required parameters'})
            return
            
        # Find messages to mark as read
        query = ChatMessage.query.filter_by(chat_id=chat_id, read=False)
        
        # If admin is reading, only mark user messages
        # If user is reading, only mark admin messages
        if is_admin:
            query = query.filter_by(is_admin=False)
        else:
            query = query.filter_by(is_admin=True)
            
        # If last_read_id is provided, only mark messages up to that ID
        if last_read_id:
            query = query.filter(ChatMessage.id <= last_read_id)
            
        # Update messages
        messages = query.all()
        for message in messages:
            message.read = True
            
        db.session.commit()
        
        # Notify the room that messages were read
        emit('messages_read', {
            'chat_id': chat_id,
            'reader_id': user_id,
            'is_admin': is_admin,
            'last_read_id': last_read_id or (messages[-1].id if messages else None)
        }, room=chat_id)
    except Exception as e:
        logger.error(f"Error in mark_messages_read handler: {str(e)}")
        emit('error', {'message': 'An error occurred while marking messages as read'})

@socketio.on('typing_status')
def handle_typing_status(data):
    """
    Broadcast typing status to the chat room
    
    Args:
        data: Dict containing chat_id, user_id, and is_typing status
    """
    try:
        chat_id = data.get('chat_id')
        user_id = data.get('user_id')
        is_typing = data.get('is_typing', False)
        is_admin = data.get('is_admin', False)
        
        if not chat_id or not user_id:
            return
            
        # Broadcast to the room except the sender
        emit('user_typing', {
            'chat_id': chat_id,
            'user_id': user_id,
            'is_admin': is_admin,
            'is_typing': is_typing
        }, room=chat_id, include_self=False)
    except Exception as e:
        logger.error(f"Error in typing_status handler: {str(e)}")

@socketio.on('get_support_status')
def handle_get_support_status():
    """Send the current status of support staff availability"""
    try:
        # Check if any support staff is online
        support_available = any(data.get('online', False) for data in support_staff.values())
        
        emit('support_status', {
            'available': support_available,
            'online_count': sum(1 for data in support_staff.values() if data.get('online', False))
        })
    except Exception as e:
        logger.error(f"Error in get_support_status handler: {str(e)}")
        emit('error', {'message': 'An error occurred while getting support status'})

def is_support_available():
    """
    Check if support staff is available
    
    Returns:
        Boolean indicating if any support staff is online
    """
    return any(data.get('online', False) for data in support_staff.values())

def get_waiting_chats_count():
    """
    Get the count of chats waiting for support
    
    Returns:
        Integer count of waiting chats
    """
    return SupportChat.query.filter_by(status='waiting').count()

def get_active_chats_count():
    """
    Get the count of currently active chats
    
    Returns:
        Integer count of active chats
    """
    return SupportChat.query.filter_by(status='active').count()