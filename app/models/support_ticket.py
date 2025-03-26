# app/models/support_ticket.py
from datetime import datetime
from app import db

class SupportTicket(db.Model):
    __tablename__ = 'support_ticket'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    ticket_number = db.Column(db.String(10), unique=True, nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='open')  # open, in_progress, closed
    priority = db.Column(db.String(20), default='normal')  # low, normal, high, urgent
    attachment_path = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship with User
    user = db.relationship('User', backref=db.backref('support_tickets', lazy='dynamic'))
    
    # Relationship with responses (one ticket to many responses)
    responses = db.relationship('TicketResponse', backref='ticket', lazy='dynamic', cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"SupportTicket(#{self.ticket_number}, User: {self.user_id}, Status: {self.status})"

class TicketResponse(db.Model):
    __tablename__ = 'ticket_response'
    
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('support_ticket.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Null means admin response
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Admin who responded
    message = db.Column(db.Text, nullable=False)
    attachment_path = db.Column(db.String(255), nullable=True)
    is_admin_response = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with User (for user responses)
    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('ticket_responses', lazy='dynamic'))
    
    # Relationship with User (for admin responses)
    admin = db.relationship('User', foreign_keys=[admin_id])
    
    def __repr__(self):
        response_type = "Admin" if self.is_admin_response else "User"
        return f"TicketResponse({response_type}, Ticket: {self.ticket_id})"