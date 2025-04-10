# app/services/email_notification_service.py
"""
Email notification service for sending various types of notifications.
This service uses a separate SMTP configuration from the OTP service.
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from datetime import datetime
import os
from app.models.user import User
from app.config import Config

logger = logging.getLogger(__name__)

class EmailNotificationService:
    """
    Service class for handling all types of email notifications with a dedicated SMTP config.
    """
    
    # Using SMTP Configuration from Config class
    @classmethod
    def _get_mail_config(cls):
        """Get mail configuration from Config object"""
        return {
            'server': Config.NOTIFICATION_MAIL_SERVER,
            'port': Config.NOTIFICATION_MAIL_PORT,
            'use_ssl': Config.NOTIFICATION_MAIL_USE_SSL,
            'use_tls': Config.NOTIFICATION_MAIL_USE_TLS,
            'username': Config.NOTIFICATION_MAIL_USERNAME,
            'password': Config.NOTIFICATION_MAIL_PASSWORD,
            'default_sender': Config.NOTIFICATION_MAIL_DEFAULT_SENDER
        }
    
    @classmethod
    def send_email(cls, to_email, subject, html_content, text_content=None, attachments=None):
        """
        Send an email using the notification SMTP configuration.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML content of the email
            text_content: Plain text content (optional, for fallback)
            attachments: List of attachment paths (optional)
        
        Returns:
            Boolean indicating success or failure
        """
        try:
            # Create message
            message = MIMEMultipart('alternative')
            message['From'] = cls._get_mail_config()['default_sender']
            message['To'] = to_email
            message['Subject'] = subject
            
            # Add text part if provided, otherwise create a simple version from HTML
            if text_content:
                message.attach(MIMEText(text_content, 'plain'))
            else:
                # Very simple HTML to text conversion
                simple_text = html_content.replace('<p>', '').replace('</p>', '\n\n')
                simple_text = simple_text.replace('<br>', '\n').replace('<br/>', '\n')
                simple_text = simple_text.replace('&nbsp;', ' ')
                
                # Remove all other HTML tags
                while '<' in simple_text and '>' in simple_text:
                    start = simple_text.find('<')
                    end = simple_text.find('>', start)
                    if start != -1 and end != -1:
                        simple_text = simple_text[:start] + simple_text[end+1:]
                    else:
                        break
                
                message.attach(MIMEText(simple_text, 'plain'))
            
            # Add HTML part
            message.attach(MIMEText(html_content, 'html'))
            
            # Add attachments if any
            if attachments:
                for attachment_path in attachments:
                    with open(attachment_path, 'rb') as f:
                        attachment = MIMEImage(f.read())
                        attachment.add_header('Content-Disposition', 'attachment', filename=os.path.basename(attachment_path))
                        message.attach(attachment)
            
            # Connect to SMTP server
            if Config.ENVIRONMENT == 'development':
                # Log email in development
                logger.info(f"Email to {to_email}: {subject}\n{html_content}")
                return True
            
            # Get mail config
            mail_config = cls._get_mail_config()
            
            # In production, actually send the email
            if mail_config['use_ssl']:
                server = smtplib.SMTP_SSL(mail_config['server'], mail_config['port'])
            else:
                server = smtplib.SMTP(mail_config['server'], mail_config['port'])
                if mail_config['use_tls']:
                    server.starttls()
            
            # Login if credentials are provided
            if mail_config['username'] and mail_config['password']:
                server.login(mail_config['username'], mail_config['password'])
            
            # Send email
            server.send_message(message)
            server.quit()
            
            logger.info(f"Notification email sent to {to_email}: {subject}")
            return True
        except Exception as e:
            logger.error(f"Error sending notification email: {str(e)}")
            return False

    @classmethod
    def send_trade_signal_notification(cls, user, signal):
        """
        Send a notification about a new trading signal.
        
        Args:
            user: User object to notify
            signal: TradeSignal object
        
        Returns:
            Boolean indicating success or failure
        """
        subject = f"New Trading Signal: {signal.currency_pair} {signal.signal_type.upper()}"
        
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; color: #333; line-height: 1.6; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 5px; }}
                .header {{ background-color: #7B68EE; color: white; padding: 10px 20px; border-radius: 5px 5px 0 0; }}
                .header h1 {{ margin: 0; font-size: 24px; }}
                .content {{ padding: 20px; }}
                .signal-details {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
                .action-button {{ display: inline-block; background-color: #7B68EE; color: white; text-decoration: none; padding: 10px 20px; border-radius: 5px; margin-top: 20px; }}
                .footer {{ font-size: 12px; color: #777; margin-top: 30px; border-top: 1px solid #e0e0e0; padding-top: 10px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>New Trading Signal</h1>
                </div>
                <div class="content">
                    <p>Hello {user.username},</p>
                    <p>A new trading signal has been published by our trading experts. Here are the details:</p>
                    
                    <div class="signal-details">
                        <p><strong>Pair:</strong> {signal.currency_pair}</p>
                        <p><strong>Type:</strong> {signal.signal_type.upper()}</p>
                        <p><strong>Entry Price:</strong> ${signal.entry_price}</p>
                        <p><strong>Target Price:</strong> ${signal.target_price}</p>
                        <p><strong>Stop Loss:</strong> ${signal.stop_loss}</p>
                        <p><strong>Leverage:</strong> {signal.leverage}x</p>
                        {f'<p><strong>Description:</strong> {signal.description}</p>' if signal.description else ''}
                    </div>
                    
                    <p>This signal will expire on {signal.expiry_time.strftime('%Y-%m-%d %H:%M:%S')} UTC.</p>
                    <p>Log in to the platform now to take action on this signal before it expires!</p>
                    
                    <a href="https://theinvestro.io/trade/signals" class="action-button">View Signal Details</a>
                    
                    <div class="footer">
                        <p>This is an automated message. Please do not reply to this email.</p>
                        <p>&copy; {datetime.utcnow().year} Investro. All rights reserved.</p>
                        <p>If you don't want to receive these notifications, you can adjust your notification settings in your account.</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        New Trading Signal: {signal.currency_pair} {signal.signal_type.upper()}
        
        Hello {user.username},
        
        A new trading signal has been published by our trading experts. Here are the details:
        
        Pair: {signal.currency_pair}
        Type: {signal.signal_type.upper()}
        Entry Price: ${signal.entry_price}
        Target Price: ${signal.target_price}
        Stop Loss: ${signal.stop_loss}
        Leverage: {signal.leverage}x
        {f'Description: {signal.description}' if signal.description else ''}
        
        This signal will expire on {signal.expiry_time.strftime('%Y-%m-%d %H:%M:%S')} UTC.
        
        Log in to the platform now to take action on this signal before it expires!
        https://theinvestro.io/trade/signals
        
        This is an automated message. Please do not reply to this email.
        © {datetime.utcnow().year} Investro. All rights reserved.
        """
        
        return cls.send_email(user.email, subject, html_content, text_content)

    @classmethod
    def send_transaction_notification(cls, user, transaction):
        """
        Send a notification about a transaction.
        
        Args:
            user: User object
            transaction: Transaction object
        
        Returns:
            Boolean indicating success or failure
        """
        # Format transaction type properly for email
        transaction_types = {
            'deposit': 'Deposit',
            'withdrawal': 'Withdrawal',
            'convert': 'Currency Conversion',
            'transfer': 'Wallet Transfer',
            'pay': 'Payment'
        }
        
        # Get formatted transaction type
        tx_type = transaction_types.get(transaction.transaction_type, transaction.transaction_type.capitalize())
        
        # Format amount with sign
        if transaction.transaction_type == 'deposit' or (transaction.transaction_type == 'pay' and transaction.amount > 0):
            amount_formatted = f"+{transaction.amount} {transaction.currency}"
        else:
            amount_formatted = f"{transaction.amount} {transaction.currency}"
        
        # Create email subject
        subject = f"{tx_type} {transaction.status.capitalize()}: {amount_formatted}"
        
        # Choose appropriate color based on transaction type
        colors = {
            'deposit': '#28a745',  # Green
            'withdrawal': '#dc3545',  # Red
            'convert': '#17a2b8',  # Teal
            'transfer': '#6c757d',  # Gray
            'pay': '#007bff'  # Blue
        }
        
        header_color = colors.get(transaction.transaction_type, '#7B68EE')
        
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; color: #333; line-height: 1.6; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 5px; }}
                .header {{ background-color: {header_color}; color: white; padding: 10px 20px; border-radius: 5px 5px 0 0; }}
                .header h1 {{ margin: 0; font-size: 24px; }}
                .content {{ padding: 20px; }}
                .transaction-details {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
                .status-badge {{ display: inline-block; padding: 5px 10px; border-radius: 3px; font-weight: bold; }}
                .status-completed {{ background-color: #28a745; color: white; }}
                .status-pending {{ background-color: #ffc107; color: black; }}
                .status-failed {{ background-color: #dc3545; color: white; }}
                .footer {{ font-size: 12px; color: #777; margin-top: 30px; border-top: 1px solid #e0e0e0; padding-top: 10px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{tx_type} {transaction.status.capitalize()}</h1>
                </div>
                <div class="content">
                    <p>Hello {user.username},</p>
                    <p>Your {transaction.transaction_type} has been {transaction.status}.</p>
                    
                    <div class="transaction-details">
                        <p><strong>Amount:</strong> {amount_formatted}</p>
                        <p><strong>Status:</strong> <span class="status-badge status-{transaction.status}">{transaction.status.upper()}</span></p>
                        <p><strong>Date:</strong> {transaction.updated_at.strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
                        <p><strong>Transaction ID:</strong> {transaction.transaction_id}</p>
                        {f'<p><strong>Fee:</strong> {transaction.fee} {transaction.currency}</p>' if transaction.fee else ''}
                        {f'<p><strong>From:</strong> {transaction.from_wallet}</p>' if transaction.from_wallet else ''}
                        {f'<p><strong>To:</strong> {transaction.to_wallet}</p>' if transaction.to_wallet else ''}
                        {f'<p><strong>Blockchain TxID:</strong> {transaction.blockchain_txid}</p>' if transaction.blockchain_txid else ''}
                        {f'<p><strong>Notes:</strong> {transaction.notes}</p>' if transaction.notes else ''}
                    </div>
                    
                    <p>You can view the details of this transaction in your account transaction history.</p>
                    
                    <div class="footer">
                        <p>This is an automated message. Please do not reply to this email.</p>
                        <p>&copy; {datetime.utcnow().year} Investro. All rights reserved.</p>
                        <p>If you have any questions, please contact our support team.</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        {tx_type} {transaction.status.capitalize()}: {amount_formatted}
        
        Hello {user.username},
        
        Your {transaction.transaction_type} has been {transaction.status}.
        
        Amount: {amount_formatted}
        Status: {transaction.status.upper()}
        Date: {transaction.updated_at.strftime('%Y-%m-%d %H:%M:%S')} UTC
        Transaction ID: {transaction.transaction_id}
        {f'Fee: {transaction.fee} {transaction.currency}' if transaction.fee else ''}
        {f'From: {transaction.from_wallet}' if transaction.from_wallet else ''}
        {f'To: {transaction.to_wallet}' if transaction.to_wallet else ''}
        {f'Blockchain TxID: {transaction.blockchain_txid}' if transaction.blockchain_txid else ''}
        {f'Notes: {transaction.notes}' if transaction.notes else ''}
        
        You can view the details of this transaction in your account transaction history.
        
        This is an automated message. Please do not reply to this email.
        © {datetime.utcnow().year} Investro. All rights reserved.
        """
        
        return cls.send_email(user.email, subject, html_content, text_content)

    @classmethod
    def send_referral_notification(cls, user, reward):
        """
        Send a notification about a referral reward.
        
        Args:
            user: User object who received the reward
            reward: ReferralReward object
        
        Returns:
            Boolean indicating success or failure
        """
        subject = f"You've Earned a Referral Reward: {reward.amount} {reward.currency}!"
        
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; color: #333; line-height: 1.6; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 5px; }}
                .header {{ background-color: #ffc107; color: #333; padding: 10px 20px; border-radius: 5px 5px 0 0; }}
                .header h1 {{ margin: 0; font-size: 24px; }}
                .content {{ padding: 20px; }}
                .reward-details {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
                .reward-amount {{ font-size: 24px; font-weight: bold; color: #28a745; }}
                .action-button {{ display: inline-block; background-color: #7B68EE; color: white; text-decoration: none; padding: 10px 20px; border-radius: 5px; margin-top: 20px; }}
                .footer {{ font-size: 12px; color: #777; margin-top: 30px; border-top: 1px solid #e0e0e0; padding-top: 10px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Referral Reward Received!</h1>
                </div>
                <div class="content">
                    <p>Hello {user.username},</p>
                    <p>Great news! You've earned a referral reward for referring a user who has met all the qualifying criteria.</p>
                    
                    <div class="reward-details">
                        <p>Your referral reward of <span class="reward-amount">{reward.amount} {reward.currency}</span> has been added to your account.</p>
                        <p><strong>Referred User:</strong> {reward.referred_username}</p>
                        <p><strong>Status:</strong> {reward.status.capitalize()}</p>
                        <p><strong>Date:</strong> {reward.created_at.strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
                    </div>
                    
                    <p>Keep referring friends and earn more rewards!</p>
                    
                    <a href="https://theinvestro.io/user/referral" class="action-button">View Your Referrals</a>
                    
                    <div class="footer">
                        <p>This is an automated message. Please do not reply to this email.</p>
                        <p>&copy; {datetime.utcnow().year} Investro. All rights reserved.</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        You've Earned a Referral Reward: {reward.amount} {reward.currency}!
        
        Hello {user.username},
        
        Great news! You've earned a referral reward for referring a user who has met all the qualifying criteria.
        
        Your referral reward of {reward.amount} {reward.currency} has been added to your account.
        
        Referred User: {reward.referred_username}
        Status: {reward.status.capitalize()}
        Date: {reward.created_at.strftime('%Y-%m-%d %H:%M:%S')} UTC
        
        Keep referring friends and earn more rewards!
        
        View your referrals at: https://theinvestro.io/user/referral
        
        This is an automated message. Please do not reply to this email.
        © {datetime.utcnow().year} Investro. All rights reserved.
        """
        
        return cls.send_email(user.email, subject, html_content, text_content)

    @classmethod
    def send_support_ticket_notification(cls, user, ticket, response=None, is_new_ticket=False):
        """
        Send a notification about a support ticket update.
        
        Args:
            user: User object who owns the ticket
            ticket: SupportTicket object
            response: TicketResponse object or None
            is_new_ticket: Boolean indicating if this is a new ticket confirmation
        
        Returns:
            Boolean indicating success or failure
        """
        if is_new_ticket:
            subject = f"Support Ticket #{ticket.ticket_number} Created"
            
            html_content = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; color: #333; line-height: 1.6; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 5px; }}
                    .header {{ background-color: #17a2b8; color: white; padding: 10px 20px; border-radius: 5px 5px 0 0; }}
                    .header h1 {{ margin: 0; font-size: 24px; }}
                    .content {{ padding: 20px; }}
                    .ticket-details {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
                    .action-button {{ display: inline-block; background-color: #7B68EE; color: white; text-decoration: none; padding: 10px 20px; border-radius: 5px; margin-top: 20px; }}
                    .footer {{ font-size: 12px; color: #777; margin-top: 30px; border-top: 1px solid #e0e0e0; padding-top: 10px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Support Ticket Created</h1>
                    </div>
                    <div class="content">
                        <p>Hello {user.username},</p>
                        <p>Your support ticket has been created successfully. Our team will review it shortly.</p>
                        
                        <div class="ticket-details">
                            <p><strong>Ticket Number:</strong> {ticket.ticket_number}</p>
                            <p><strong>Subject:</strong> {ticket.subject}</p>
                            <p><strong>Category:</strong> {ticket.category}</p>
                            <p><strong>Status:</strong> {ticket.status.upper()}</p>
                            <p><strong>Created:</strong> {ticket.created_at.strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
                        </div>
                        
                        <p>You can view the status of your ticket at any time by logging into your account.</p>
                        
                        <a href="https://theinvestro.io/user/support/ticket/{ticket.ticket_number}" class="action-button">View Ticket</a>
                        
                        <div class="footer">
                            <p>This is an automated message. Please do not reply to this email.</p>
                            <p>&copy; {datetime.utcnow().year} Investro. All rights reserved.</p>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """
            
            text_content = f"""
            Support Ticket #{ticket.ticket_number} Created
            
            Hello {user.username},
            
            Your support ticket has been created successfully. Our team will review it shortly.
            
            Ticket Number: {ticket.ticket_number}
            Subject: {ticket.subject}
            Category: {ticket.category}
            Status: {ticket.status.upper()}
            Created: {ticket.created_at.strftime('%Y-%m-%d %H:%M:%S')} UTC
            
            You can view the status of your ticket at any time by logging into your account:
            https://theinvestro.io/user/support/ticket/{ticket.ticket_number}
            
            This is an automated message. Please do not reply to this email.
            © {datetime.utcnow().year} Investro. All rights reserved.
            """
        
        else:  # Ticket update notification
            subject = f"Update on Support Ticket #{ticket.ticket_number}"
            
            # Determine if it's a status change or new response
            if response:
                update_text = "A new response has been added to your ticket."
                responder = "Support Team" if response.is_admin_response else user.username
                response_text = f"""
                <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin-top: 15px; border-left: 3px solid #17a2b8;">
                    <p><strong>From:</strong> {responder}</p>
                    <p><strong>Date:</strong> {response.created_at.strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
                    <p style="white-space: pre-wrap;">{response.message}</p>
                </div>
                """
                
                text_response = f"""
                --- New Response ---
                From: {responder}
                Date: {response.created_at.strftime('%Y-%m-%d %H:%M:%S')} UTC
                
                {response.message}
                """
            else:
                update_text = f"The status of your ticket has been updated to {ticket.status.upper()}."
                response_text = ""
                text_response = ""
            
            html_content = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; color: #333; line-height: 1.6; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 5px; }}
                    .header {{ background-color: #17a2b8; color: white; padding: 10px 20px; border-radius: 5px 5px 0 0; }}
                    .header h1 {{ margin: 0; font-size: 24px; }}
                    .content {{ padding: 20px; }}
                    .ticket-details {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
                    .action-button {{ display: inline-block; background-color: #7B68EE; color: white; text-decoration: none; padding: 10px 20px; border-radius: 5px; margin-top: 20px; }}
                    .footer {{ font-size: 12px; color: #777; margin-top: 30px; border-top: 1px solid #e0e0e0; padding-top: 10px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Support Ticket Update</h1>
                    </div>
                    <div class="content">
                        <p>Hello {user.username},</p>
                        <p>{update_text}</p>
                        
                        <div class="ticket-details">
                            <p><strong>Ticket Number:</strong> {ticket.ticket_number}</p>
                            <p><strong>Subject:</strong> {ticket.subject}</p>
                            <p><strong>Status:</strong> {ticket.status.upper()}</p>
                            <p><strong>Last Updated:</strong> {ticket.updated_at.strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
                        </div>
                        
                        {response_text}
                        
                        <p>You can view the full ticket details and respond by logging into your account.</p>
                        
                        <a href="https://theinvestro.io/user/support/ticket/{ticket.ticket_number}" class="action-button">View Ticket</a>
                        
                        <div class="footer">
                            <p>This is an automated message. Please do not reply to this email.</p>
                            <p>&copy; {datetime.utcnow().year} Investro. All rights reserved.</p>
                            <p>If you have any questions, please log in and respond to your ticket.</p>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """
            
            text_content = f"""
            Update on Support Ticket #{ticket.ticket_number}
            
            Hello {user.username},
            
            {update_text}
            
            Ticket Number: {ticket.ticket_number}
            Subject: {ticket.subject}
            Status: {ticket.status.upper()}
            Last Updated: {ticket.updated_at.strftime('%Y-%m-%d %H:%M:%S')} UTC
            
            {text_response}
            
            You can view the full ticket details and respond by logging into your account:
            https://theinvestro.io/user/support/ticket/{ticket.ticket_number}
            
            This is an automated message. Please do not reply to this email.
            © {datetime.utcnow().year} Investro. All rights reserved.
            """
        
        return cls.send_email(user.email, subject, html_content, text_content)

    @classmethod
    def send_verification_status_notification(cls, user, verification_status, admin_notes=None):
        """
        Send a notification about a change in verification status.
        
        Args:
            user: User object
            verification_status: New verification status ('approved' or 'rejected')
            admin_notes: Optional notes from admin
        
        Returns:
            Boolean indicating success or failure
        """
        if verification_status == 'approved':
            subject = "Identity Verification Approved"
            header_color = "#28a745"  # Green
            status_message = "Your identity verification has been approved! Your account is now fully verified."
            intro_message = "Congratulations! Your identity verification has been successfully approved."
        else:
            subject = "Identity Verification Rejected"
            header_color = "#dc3545"  # Red
            status_message = "Your identity verification has been rejected. Please review the admin notes and submit new documents."
            intro_message = "Unfortunately, your identity verification has been rejected."
        
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; color: #333; line-height: 1.6; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 5px; }}
                .header {{ background-color: {header_color}; color: white; padding: 10px 20px; border-radius: 5px 5px 0 0; }}
                .header h1 {{ margin: 0; font-size: 24px; }}
                .content {{ padding: 20px; }}
                .verification-details {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
                .action-button {{ display: inline-block; background-color: #7B68EE; color: white; text-decoration: none; padding: 10px 20px; border-radius: 5px; margin-top: 20px; }}
                .footer {{ font-size: 12px; color: #777; margin-top: 30px; border-top: 1px solid #e0e0e0; padding-top: 10px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Verification {verification_status.capitalize()}</h1>
                </div>
                <div class="content">
                    <p>Hello {user.username},</p>
                    <p>{intro_message}</p>
                    
                    <div class="verification-details">
                        <p>{status_message}</p>
                        {f'<p><strong>Admin Notes:</strong> {admin_notes}</p>' if admin_notes else ''}
                    </div>
                    
                    {f'<p>You can now access all features of our platform, including deposits, withdrawals, and trading.</p>' if verification_status == 'approved' else '<p>You can submit new verification documents by visiting the verification page in your account settings.</p>'}
                    
                    <a href="https://theinvestro.io/user/verification" class="action-button">Verification Page</a>
                    
                    <div class="footer">
                        <p>This is an automated message. Please do not reply to this email.</p>
                        <p>&copy; {datetime.utcnow().year} Investro. All rights reserved.</p>
                        <p>If you have any questions, please contact our support team.</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Verification {verification_status.capitalize()}
        
        Hello {user.username},
        
        {intro_message}
        
        {status_message}
        {f'Admin Notes: {admin_notes}' if admin_notes else ''}
        
        {f'You can now access all features of our platform, including deposits, withdrawals, and trading.' if verification_status == 'approved' else 'You can submit new verification documents by visiting the verification page in your account settings.'}
        
        Verification Page: https://theinvestro.io/user/verification
        
        This is an automated message. Please do not reply to this email.
        © {datetime.utcnow().year} Investro. All rights reserved.
        """
        
        return cls.send_email(user.email, subject, html_content, text_content)

    @classmethod
    def send_welcome_email(cls, user):
        """
        Send a welcome email to a new user.
        
        Args:
            user: User object
        
        Returns:
            Boolean indicating success or failure
        """
        subject = f"Welcome to Investro, {user.username}!"
        
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; color: #333; line-height: 1.6; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 5px; }}
                .header {{ background: linear-gradient(90deg, #7B68EE, #9370DB); color: white; padding: 20px; border-radius: 5px 5px 0 0; text-align: center; }}
                .header h1 {{ margin: 0; font-size: 28px; }}
                .content {{ padding: 20px; }}
                .welcome-image {{ width: 100%; max-width: 500px; height: auto; margin: 20px 0; }}
                .steps {{ background-color: #f5f5f5; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
                .step {{ margin-bottom: 15px; }}
                .step-number {{ display: inline-block; width: 30px; height: 30px; background-color: #7B68EE; color: white; border-radius: 50%; text-align: center; line-height: 30px; margin-right: 10px; font-weight: bold; }}
                .action-button {{ display: inline-block; background-color: #7B68EE; color: white; text-decoration: none; padding: 15px 25px; border-radius: 5px; margin-top: 20px; font-weight: bold; text-align: center; }}
                .footer {{ font-size: 12px; color: #777; margin-top: 30px; border-top: 1px solid #e0e0e0; padding-top: 20px; text-align: center; }}
                .social-links {{ margin-top: 15px; }}
                .social-link {{ display: inline-block; margin: 0 10px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Welcome to Investro!</h1>
                </div>
                <div class="content">
                    <p>Hello {user.username},</p>
                    <p>Thank you for joining Investro! We're excited to have you on board and help you on your journey to successful trading.</p>
                    
                    <div class="steps">
                        <h2>Getting Started</h2>
                        <div class="step">
                            <span class="step-number">1</span>
                            <strong>Complete your profile</strong> - Add any missing information to your account settings.
                        </div>
                        <div class="step">
                            <span class="step-number">2</span>
                            <strong>Verify your identity</strong> - Submit your verification documents to unlock all platform features.
                        </div>
                        <div class="step">
                            <span class="step-number">3</span>
                            <strong>Make your first deposit</strong> - Fund your account to start trading.
                        </div>
                        <div class="step">
                            <span class="step-number">4</span>
                            <strong>Follow trading signals</strong> - Get expert guidance with our professional trading signals.
                        </div>
                    </div>
                    
                    <p>Our platform offers a range of features designed to help both beginners and experienced traders:</p>
                    <ul>
                        <li>Real-time trading signals from expert analysts</li>
                        <li>Secure wallet management</li>
                        <li>Detailed transaction history</li>
                        <li>Instant currency conversions</li>
                        <li>Peer-to-peer payments</li>
                        <li>Referral program to earn rewards</li>
                    </ul>
                    
                    <p>If you have any questions or need assistance, our support team is always ready to help.</p>
                    
                    <div style="text-align: center;">
                        <a href="https://theinvestro.io/user/home" class="action-button">Go to Dashboard</a>
                    </div>
                    
                    <div class="footer">
                        <p>This is an automated message. Please do not reply to this email.</p>
                        <p>&copy; {datetime.utcnow().year} Investro. All rights reserved.</p>
                        <div class="social-links">
                            <a href="https://t.me/theinvestr0" class="social-link">Telegram</a>
                            <a href="#" class="social-link">Twitter</a>
                            <a href="#" class="social-link">Facebook</a>
                            <a href="#" class="social-link">Instagram</a>
                        </div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Welcome to Investro, {user.username}!
        
        Hello {user.username},
        
        Thank you for joining Investro! We're excited to have you on board and help you on your journey to successful trading.
        
        Getting Started:
        1. Complete your profile - Add any missing information to your account settings.
        2. Verify your identity - Submit your verification documents to unlock all platform features.
        3. Make your first deposit - Fund your account to start trading.
        4. Follow trading signals - Get expert guidance with our professional trading signals.
        
        Our platform offers a range of features designed to help both beginners and experienced traders:
        - Real-time trading signals from expert analysts
        - Secure wallet management
        - Detailed transaction history
        - Instant currency conversions
        - Peer-to-peer payments
        - Referral program to earn rewards
        
        If you have any questions or need assistance, our support team is always ready to help.
        
        Go to Dashboard: https://theinvestro.io/user/home
        
        This is an automated message. Please do not reply to this email.
        © {datetime.utcnow().year} Investro. All rights reserved.
        
        Join us on:
        Telegram: https://t.me/theinvestr0
        """
        
        return cls.send_email(user.email, subject, html_content, text_content)

    @classmethod
    def send_password_reset_email(cls, user, reset_token):
        """
        Send a password reset email with a reset link.
        
        Args:
            user: User object
            reset_token: Password reset token
        
        Returns:
            Boolean indicating success or failure
        """
        subject = "Reset Your Investro Password"
        
        # Generate reset URL (valid for limited time)
        reset_url = f"https://theinvestro.io/auth/reset-password?token={reset_token}"
        
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; color: #333; line-height: 1.6; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 5px; }}
                .header {{ background-color: #7B68EE; color: white; padding: 10px 20px; border-radius: 5px 5px 0 0; }}
                .header h1 {{ margin: 0; font-size: 24px; }}
                .content {{ padding: 20px; }}
                .reset-box {{ background-color: #f5f5f5; padding: 20px; border-radius: 5px; margin: 20px 0; text-align: center; }}
                .reset-button {{ display: inline-block; background-color: #7B68EE; color: white; text-decoration: none; padding: 12px 25px; border-radius: 5px; font-weight: bold; }}
                .security-note {{ background-color: #fff8e1; border-left: 4px solid #ffc107; padding: 15px; margin-top: 20px; }}
                .footer {{ font-size: 12px; color: #777; margin-top: 30px; border-top: 1px solid #e0e0e0; padding-top: 10px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Password Reset Request</h1>
                </div>
                <div class="content">
                    <p>Hello {user.username},</p>
                    <p>We received a request to reset your Investro account password. If you didn't make this request, you can safely ignore this email.</p>
                    
                    <div class="reset-box">
                        <p>To reset your password, click the button below:</p>
                        <a href="{reset_url}" class="reset-button">Reset Password</a>
                        <p style="margin-top: 15px; font-size: 12px;">Or copy and paste this URL into your browser:</p>
                        <p style="margin-top: 5px; font-size: 12px; word-break: break-all;">{reset_url}</p>
                    </div>
                    
                    <div class="security-note">
                        <p><strong>Security Note:</strong> This password reset link will expire in 30 minutes. If you need a new link, please request another password reset.</p>
                    </div>
                    
                    <div class="footer">
                        <p>This is an automated message. Please do not reply to this email.</p>
                        <p>&copy; {datetime.utcnow().year} Investro. All rights reserved.</p>
                        <p>If you did not request a password reset, please secure your account and contact our support team immediately.</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Reset Your Investro Password
        
        Hello {user.username},
        
        We received a request to reset your Investro account password. If you didn't make this request, you can safely ignore this email.
        
        To reset your password, click the link below:
        {reset_url}
        
        Security Note: This password reset link will expire in 30 minutes. If you need a new link, please request another password reset.
        
        This is an automated message. Please do not reply to this email.
        © {datetime.utcnow().year} Investro. All rights reserved.
        
        If you did not request a password reset, please secure your account and contact our support team immediately.
        """
        
        return cls.send_email(user.email, subject, html_content, text_content)

    @classmethod
    def send_security_alert(cls, user, action, ip_address, device_info, location=None):
        """
        Send a security alert notification for important account activities.
        
        Args:
            user: User object
            action: Action performed (login, password change, etc.)
            ip_address: IP address from which the action was performed
            device_info: Device information
            location: Approximate location (optional)
        
        Returns:
            Boolean indicating success or failure
        """
        subject = f"Security Alert: {action}"
        
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; color: #333; line-height: 1.6; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 5px; }}
                .header {{ background-color: #dc3545; color: white; padding: 10px 20px; border-radius: 5px 5px 0 0; }}
                .header h1 {{ margin: 0; font-size: 24px; }}
                .content {{ padding: 20px; }}
                .activity-details {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
                .action-list {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-top: 20px; }}
                .action-item {{ margin-bottom: 10px; }}
                .footer {{ font-size: 12px; color: #777; margin-top: 30px; border-top: 1px solid #e0e0e0; padding-top: 10px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Security Alert</h1>
                </div>
                <div class="content">
                    <p>Hello {user.username},</p>
                    <p>We detected the following activity on your Investro account:</p>
                    
                    <div class="activity-details">
                        <p><strong>Action:</strong> {action}</p>
                        <p><strong>Time:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
                        <p><strong>IP Address:</strong> {ip_address}</p>
                        <p><strong>Device:</strong> {device_info}</p>
                        {f'<p><strong>Location:</strong> {location}</p>' if location else ''}
                    </div>
                    
                    <p><strong>If this was you</strong>, you can ignore this message.</p>
                    
                    <p><strong>If you didn't perform this action</strong>, please secure your account immediately:</p>
                    
                    <div class="action-list">
                        <div class="action-item">1. <strong>Change your password</strong> immediately.</div>
                        <div class="action-item">2. <strong>Set a new withdrawal PIN</strong> in your account settings.</div>
                        <div class="action-item">3. <strong>Contact our support team</strong> for assistance.</div>
                    </div>
                    
                    <div class="footer">
                        <p>This is an automated message. Please do not reply to this email.</p>
                        <p>&copy; {datetime.utcnow().year} Investro. All rights reserved.</p>
                        <p>For security reasons, we regularly monitor account activity and send notifications for significant actions.</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Security Alert: {action}
        
        Hello {user.username},
        
        We detected the following activity on your Investro account:
        
        Action: {action}
        Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
        IP Address: {ip_address}
        Device: {device_info}
        {f'Location: {location}' if location else ''}
        
        If this was you, you can ignore this message.
        
        If you didn't perform this action, please secure your account immediately:
        
        1. Change your password immediately.
        2. Set a new withdrawal PIN in your account settings.
        3. Contact our support team for assistance.
        
        This is an automated message. Please do not reply to this email.
        © {datetime.utcnow().year} Investro. All rights reserved.
        """
        
        return cls.send_email(user.email, subject, html_content, text_content)

# Convenience functions for calling from other parts of the application

def send_trade_signal_notification(user, signal):
    """Convenience function for sending trade signal notifications"""
    return EmailNotificationService.send_trade_signal_notification(user, signal)

def send_transaction_notification(user, transaction):
    """Convenience function for sending transaction notifications"""
    return EmailNotificationService.send_transaction_notification(user, transaction)

def send_referral_notification(user, reward):
    """Convenience function for sending referral notifications"""
    return EmailNotificationService.send_referral_notification(user, reward)

def send_support_ticket_notification(user, ticket, response=None, is_new_ticket=False):
    """Convenience function for sending support ticket notifications"""
    return EmailNotificationService.send_support_ticket_notification(user, ticket, response, is_new_ticket)

def send_verification_status_notification(user, verification_status, admin_notes=None):
    """Convenience function for sending verification status notifications"""
    return EmailNotificationService.send_verification_status_notification(user, verification_status, admin_notes)

def send_welcome_email(user):
    """Convenience function for sending welcome emails"""
    return EmailNotificationService.send_welcome_email(user)

def send_password_reset_email(user, reset_token):
    """Convenience function for sending password reset emails"""
    return EmailNotificationService.send_password_reset_email(user, reset_token)

def send_security_alert(user, action, ip_address, device_info, location=None):
    """Convenience function for sending security alerts"""
    return EmailNotificationService.send_security_alert(user, action, ip_address, device_info, location)