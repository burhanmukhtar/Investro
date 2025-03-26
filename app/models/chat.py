# app/models/chat.py
"""
Models for chat and support ticket functionality.
Includes models for support tickets, chat sessions, and messages.
"""
from datetime import datetime
from app import db

class SupportTicket(db.Model):
    """
    Model for support tickets created by users.
    """
    __tablename__ = 'support_ticket'
    
    id = db.Column(db.Integer, primary_key=True)
    ticket_number = db.Column(db.String(20), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='open')  # open, in_progress, closed, reopened
    priority = db.Column(db.String(20), default='medium')  # low, medium, high, urgent
    attachment_path = db.Column(db.String(255), nullable=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    closed_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='support_tickets')
    admin = db.relationship('User', foreign_keys=[admin_id], backref='assigned_tickets')
    responses = db.relationship('TicketResponse', backref='ticket', lazy=True, cascade="all, delete-orphan")
    chat = db.relationship('SupportChat', backref='ticket', uselist=False, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"SupportTicket(#{self.ticket_number}, Subject: {self.subject}, Status: {self.status})"

class TicketResponse(db.Model):
    """
    Model for responses to support tickets.
    """
    __tablename__ = 'ticket_response'
    
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('support_ticket.id'), nullable=False)
    responder_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    attachment_path = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    responder = db.relationship('User', backref='ticket_responses')
    
    def __repr__(self):
        return f"TicketResponse(Ticket: {self.ticket_id}, Admin: {self.is_admin}, Date: {self.created_at})"

class SupportChat(db.Model):
    """
    Model for real-time support chat sessions.
    Can be linked to a support ticket or standalone.
    """
    __tablename__ = 'support_chat'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('support_ticket.id'), nullable=True)
    subject = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(20), default='new')  # new, waiting, active, closed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)
    closed_at = db.Column(db.DateTime, nullable=True)
    feedback_rating = db.Column(db.Integer, nullable=True)  # 1-5 stars
    feedback_comment = db.Column(db.Text, nullable=True)
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='support_chats')
    admin = db.relationship('User', foreign_keys=[admin_id], backref='handled_chats')
    messages = db.relationship('ChatMessage', backref='chat', lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"SupportChat(User: {self.user_id}, Status: {self.status}, Last Activity: {self.last_activity})"

class ChatMessage(db.Model):
    """
    Model for individual chat messages within a support chat.
    """
    __tablename__ = 'chat_message'
    
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, db.ForeignKey('support_chat.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    sender_name = db.Column(db.String(50), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    content = db.Column(db.Text, nullable=False)
    attachment_path = db.Column(db.String(255), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    read = db.Column(db.Boolean, default=False)
    
    # Relationship
    sender = db.relationship('User', backref='chat_messages')
    
    def __repr__(self):
        return f"ChatMessage(Chat: {self.chat_id}, Sender: {self.sender_name}, Admin: {self.is_admin}, Timestamp: {self.timestamp})"