# app/services/notification_service.py
"""
Notification service for sending emails, SMS, and push notifications.
Handles OTP verification, transaction notifications, and system announcements.
"""
import os
import smtplib
import requests
import logging
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from app.config import Config
from app.models.user import User
from app import db

logger = logging.getLogger(__name__)

class NotificationService:
    """
    Service class for handling all types of notifications.
    """
    
    @staticmethod
    def send_email(to_email, subject, html_content, text_content=None):
        """
        Send an email using SMTP.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML content of the email
            text_content: Plain text content (optional, for fallback)
        
        Returns:
            Boolean indicating success or failure
        """
        try:
            # Create message
            message = MIMEMultipart('alternative')
            message['From'] = Config.MAIL_USERNAME
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
            
            # Connect to SMTP server
            if Config.ENVIRONMENT == 'development':
                # Log email in development
                logger.info(f"Email to {to_email}: {subject}\n{html_content}")
                return True
            
            # In production, actually send the email
            server = smtplib.SMTP(Config.MAIL_SERVER, Config.MAIL_PORT)
            if Config.MAIL_USE_TLS:
                server.starttls()
            
            # Login if credentials are provided
            if Config.MAIL_USERNAME and Config.MAIL_PASSWORD:
                server.login(Config.MAIL_USERNAME, Config.MAIL_PASSWORD)
            
            # Send email
            server.send_message(message)
            server.quit()
            
            logger.info(f"Email sent to {to_email}: {subject}")
            return True
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            return False
    
    @staticmethod
    def send_sms(phone_number, message):
        """
        Send an SMS using a third-party SMS gateway.
        
        This implementation supports multiple SMS providers:
        - Twilio
        - Nexmo/Vonage
        - AWS SNS
        - Generic HTTP API
        
        Args:
            phone_number: Recipient phone number
            message: SMS content
        
        Returns:
            Boolean indicating success or failure
        """
        try:
            # In development, just log the message
            if Config.ENVIRONMENT == 'development':
                logger.info(f"SMS to {phone_number}: {message}")
                return True
            
            # In production, use the configured SMS provider
            sms_provider = Config.SMS_PROVIDER.lower()
            
            if sms_provider == 'twilio':
                return NotificationService._send_sms_twilio(phone_number, message)
            elif sms_provider == 'nexmo' or sms_provider == 'vonage':
                return NotificationService._send_sms_nexmo(phone_number, message)
            elif sms_provider == 'aws' or sms_provider == 'sns':
                return NotificationService._send_sms_aws(phone_number, message)
            else:
                # Generic HTTP API
                return NotificationService._send_sms_generic(phone_number, message)
        except Exception as e:
            logger.error(f"Error sending SMS: {str(e)}")
            return False
    
    @staticmethod
    def _send_sms_twilio(phone_number, message):
        """
        Send SMS using Twilio.
        
        Args:
            phone_number: Recipient phone number
            message: SMS content
        
        Returns:
            Boolean indicating success or failure
        """
        try:
            # Import Twilio library only when needed
            from twilio.rest import Client
            
            client = Client(Config.TWILIO_ACCOUNT_SID, Config.TWILIO_AUTH_TOKEN)
            
            client.messages.create(
                body=message,
                from_=Config.TWILIO_PHONE_NUMBER,
                to=phone_number
            )
            
            logger.info(f"Twilio SMS sent to {phone_number}")
            return True
        except ImportError:
            logger.error("Twilio library not installed. Install it with 'pip install twilio'.")
            return False
        except Exception as e:
            logger.error(f"Error sending Twilio SMS: {str(e)}")
            return False
    
    @staticmethod
    def _send_sms_nexmo(phone_number, message):
        """
        Send SMS using Nexmo/Vonage.
        
        Args:
            phone_number: Recipient phone number
            message: SMS content
        
        Returns:
            Boolean indicating success or failure
        """
        try:
            # Import Vonage library only when needed
            import vonage
            
            client = vonage.Client(key=Config.NEXMO_API_KEY, secret=Config.NEXMO_API_SECRET)
            sms = vonage.Sms(client)
            
            response = sms.send_message({
                'from': Config.NEXMO_BRAND_NAME,
                'to': phone_number,
                'text': message
            })
            
            # Check if any messages failed
            if response['messages'][0]['status'] == '0':
                logger.info(f"Nexmo SMS sent to {phone_number}")
                return True
            else:
                logger.error(f"Error sending Nexmo SMS: {response['messages'][0]['error-text']}")
                return False
        except ImportError:
            logger.error("Vonage library not installed. Install it with 'pip install vonage'.")
            return False
        except Exception as e:
            logger.error(f"Error sending Nexmo SMS: {str(e)}")
            return False
    
    @staticmethod
    def _send_sms_aws(phone_number, message):
        """
        Send SMS using AWS SNS.
        
        Args:
            phone_number: Recipient phone number
            message: SMS content
        
        Returns:
            Boolean indicating success or failure
        """
        try:
            # Import boto3 library only when needed
            import boto3
            
            client = boto3.client(
                'sns',
                region_name=Config.AWS_REGION,
                aws_access_key_id=Config.AWS_ACCESS_KEY,
                aws_secret_access_key=Config.AWS_SECRET_KEY
            )
            
            response = client.publish(
                PhoneNumber=phone_number,
                Message=message,
                MessageAttributes={
                    'AWS.SNS.SMS.SenderID': {
                        'DataType': 'String',
                        'StringValue': Config.AWS_SNS_SENDER_ID
                    }
                }
            )
            
            logger.info(f"AWS SNS SMS sent to {phone_number}: {response['MessageId']}")
            return True
        except ImportError:
            logger.error("Boto3 library not installed. Install it with 'pip install boto3'.")
            return False
        except Exception as e:
            logger.error(f"Error sending AWS SNS SMS: {str(e)}")
            return False
    
    @staticmethod
    def _send_sms_generic(phone_number, message):
        """
        Send SMS using a generic HTTP API.
        
        Args:
            phone_number: Recipient phone number
            message: SMS content
        
        Returns:
            Boolean indicating success or failure
        """
        try:
            # Replace placeholder values in URL and payload
            url = Config.SMS_API_URL
            
            # Dynamic payload based on configuration
            payload_template = Config.SMS_API_PAYLOAD
            payload = json.loads(payload_template.replace('{{phone}}', phone_number).replace('{{message}}', message))
            
            # Dynamic headers
            headers = json.loads(Config.SMS_API_HEADERS) if Config.SMS_API_HEADERS else {}
            
            # Make request
            response = requests.post(
                url,
                json=payload if 'json' in headers.get('Content-Type', '') else None,
                data=payload if 'json' not in headers.get('Content-Type', '') else None,
                headers=headers
            )
            
            if response.status_code // 100 == 2:  # 2xx status code
                logger.info(f"Generic SMS API message sent to {phone_number}")
                return True
            else:
                logger.error(f"Error sending SMS via generic API: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error sending SMS via generic API: {str(e)}")
            return False
    
    @staticmethod
    def send_push_notification(user_id, title, body, data=None):
        """
        Send a push notification to a user's device.
        
        This implementation supports multiple push notification providers:
        - Firebase Cloud Messaging (FCM)
        - OneSignal
        
        Args:
            user_id: User ID to send notification to
            title: Notification title
            body: Notification body
            data: Additional data payload (optional)
        
        Returns:
            Boolean indicating success or failure
        """
        try:
            # In development, just log the notification
            if Config.ENVIRONMENT == 'development':
                logger.info(f"Push notification to user {user_id}: {title} - {body}")
                return True
            
            # In production, use the configured push notification provider
            push_provider = Config.PUSH_PROVIDER.lower() if hasattr(Config, 'PUSH_PROVIDER') else 'fcm'
            
            if push_provider == 'onesignal':
                return NotificationService._send_push_onesignal(user_id, title, body, data)
            else:
                # Default to Firebase Cloud Messaging
                return NotificationService._send_push_fcm(user_id, title, body, data)
        except Exception as e:
            logger.error(f"Error sending push notification: {str(e)}")
            return False
    
    @staticmethod
    def _send_push_fcm(user_id, title, body, data=None):
        """
        Send push notification using Firebase Cloud Messaging.
        
        Args:
            user_id: User ID to send notification to
            title: Notification title
            body: Notification body
            data: Additional data payload (optional)
        
        Returns:
            Boolean indicating success or failure
        """
        try:
            # Get user's FCM tokens
            # In a real implementation, you would store FCM tokens in a separate table
            # For simplicity, we'll assume there's a UserDevice model
            from app.models.user import UserDevice
            
            devices = UserDevice.query.filter_by(user_id=user_id, is_active=True).all()
            if not devices:
                logger.warning(f"No active devices found for user {user_id}")
                return False
            
            # Import Firebase Admin SDK only when needed
            import firebase_admin
            from firebase_admin import credentials, messaging
            
            # Initialize Firebase app if not already initialized
            if not firebase_admin._apps:
                cred = credentials.Certificate(Config.FIREBASE_CREDENTIALS_PATH)
                firebase_admin.initialize_app(cred)
            
            # Prepare message
            message = messaging.MulticastMessage(
                notification=messaging.Notification(
                    title=title,
                    body=body
                ),
                data=data or {},
                tokens=[device.token for device in devices]
            )
            
            # Send message
            response = messaging.send_multicast(message)
            
            logger.info(f"FCM notification sent to {response.success_count} devices for user {user_id}")
            return response.success_count > 0
        except ImportError:
            logger.error("Firebase Admin SDK not installed. Install it with 'pip install firebase-admin'.")
            return False                                                                                                                         
        except Exception as e:
            logger.error(f"Error sending FCM notification: {str(e)}")
            return False
    
    @staticmethod
    def _send_push_onesignal(user_id, title, body, data=None):
        """
        Send push notification using OneSignal.
        
        Args:
            user_id: User ID to send notification to
            title: Notification title
            body: Notification body
            data: Additional data payload (optional)
        
        Returns:
            Boolean indicating success or failure
        """
        try:
            # Get user's external ID (assuming it's stored in the User model)
            user = User.query.get(user_id)
            if not user:
                logger.warning(f"User {user_id} not found")
                return False
            
            # Prepare payload
            payload = {
                "app_id": Config.ONESIGNAL_APP_ID,
                "contents": {"en": body},
                "headings": {"en": title},
                "include_external_user_ids": [str(user_id)],
                "data": data or {}
            }
            
            # Send request
            response = requests.post(
                "https://onesignal.com/api/v1/notifications",
                headers={
                    "Authorization": f"Basic {Config.ONESIGNAL_API_KEY}",
                    "Content-Type": "application/json"
                },
                json=payload
            )
            
            response_data = response.json()
            
            if response.status_code == 200 and response_data.get("id"):
                logger.info(f"OneSignal notification sent to user {user_id}: {response_data['id']}")
                return True
            else:
                logger.error(f"Error sending OneSignal notification: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error sending OneSignal notification: {str(e)}")
            return False
    
    @staticmethod
    def send_otp_notification(user, otp, method='both'):
        """
        Send OTP code to user via email, SMS, or both.
        
        Args:
            user: User object
            otp: OTP code
            method: Notification method ('email', 'sms', or 'both')
        
        Returns:
            Boolean indicating success or failure
        """
        success = True
        
        if method in ['email', 'both']:
            # Send email with OTP
            html_content = f"""
            <html>
            <body>
                <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;border:1px solid #e0e0e0;border-radius:5px;">
                    <h2 style="color:#333;">Your Verification Code</h2>
                    <p>Hello {user.username},</p>
                    <p>Your verification code is:</p>
                    <div style="background-color:#f5f5f5;padding:15px;font-size:24px;text-align:center;letter-spacing:5px;font-weight:bold;border-radius:5px;">
                        {otp}
                    </div>
                    <p style="margin-top:20px;">This code will expire in 10 minutes.</p>
                    <p>If you did not request this code, please ignore this email.</p>
                    <p style="margin-top:30px;font-size:12px;color:#777;">
                        This is an automated message. Please do not reply to this email.
                    </p>
                </div>
            </body>
            </html>
            """
            
            text_content = f"""
            Your Verification Code
            
            Hello {user.username},
            
            Your verification code is: {otp}
            
            This code will expire in 10 minutes.
            
            If you did not request this code, please ignore this email.
            """
            
            email_success = NotificationService.send_email(
                user.email, 
                "Your Verification Code", 
                html_content, 
                text_content
            )
            success = success and email_success
        
        if method in ['sms', 'both']:
            # Send SMS with OTP
            sms_content = f"Your verification code is: {otp}. It will expire in 10 minutes."
            sms_success = NotificationService.send_sms(user.phone, sms_content)
            success = success and sms_success
        
        return success
    
    @staticmethod
    def send_transaction_notification(user, transaction):
        """
        Send a notification about a transaction.
        
        Args:
            user: User object
            transaction: Transaction object
        
        Returns:
            Boolean indicating success or failure
        """
        # Format amount with sign
        if transaction.transaction_type == 'deposit' or (transaction.transaction_type == 'pay' and transaction.amount > 0):
            amount_formatted = f"+{transaction.amount}"
        else:
            amount_formatted = f"{transaction.amount}"
        
        # Create email content
        subject = f"{transaction.transaction_type.capitalize()} {transaction.status.capitalize()}: {amount_formatted} {transaction.currency}"
        
        html_content = f"""
        <html>
        <body>
            <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;border:1px solid #e0e0e0;border-radius:5px;">
                <h2 style="color:#333;">{transaction.transaction_type.capitalize()} {transaction.status.capitalize()}</h2>
                <p>Hello {user.username},</p>
                <p>Your {transaction.transaction_type} has been {transaction.status}.</p>
                <div style="background-color:#f5f5f5;padding:15px;border-radius:5px;">
                    <p><strong>Amount:</strong> {amount_formatted} {transaction.currency}</p>
                    <p><strong>Status:</strong> {transaction.status.capitalize()}</p>
                    <p><strong>Date:</strong> {transaction.updated_at.strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p><strong>Transaction ID:</strong> {transaction.transaction_id}</p>
                    {f'<p><strong>Fee:</strong> {transaction.fee} {transaction.currency}</p>' if transaction.fee else ''}
                    {f'<p><strong>Blockchain TxID:</strong> {transaction.blockchain_txid}</p>' if transaction.blockchain_txid else ''}
                </div>
                <p style="margin-top:20px;">Thank you for using our platform.</p>
                <p style="margin-top:30px;font-size:12px;color:#777;">
                    This is an automated message. Please do not reply to this email.
                </p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        {transaction.transaction_type.capitalize()} {transaction.status.capitalize()}
        
        Hello {user.username},
        
        Your {transaction.transaction_type} has been {transaction.status}.
        
        Amount: {amount_formatted} {transaction.currency}
        Status: {transaction.status.capitalize()}
        Date: {transaction.updated_at.strftime('%Y-%m-%d %H:%M:%S')}
        Transaction ID: {transaction.transaction_id}
        {f'Fee: {transaction.fee} {transaction.currency}' if transaction.fee else ''}
        {f'Blockchain TxID: {transaction.blockchain_txid}' if transaction.blockchain_txid else ''}
        
        Thank you for using our platform.
        """
        
        # Send email
        email_success = NotificationService.send_email(
            user.email, 
            subject, 
            html_content, 
            text_content
        )
        
        # Send push notification
        push_success = NotificationService.send_push_notification(
            user.id,
            subject,
            f"Your {transaction.transaction_type} of {amount_formatted} {transaction.currency} has been {transaction.status}."
        )
        
        return email_success and push_success
    
    @staticmethod
    def send_verification_notification(user, status, notes=None):
        """
        Send a notification about verification status.
        
        Args:
            user: User object
            status: Verification status ('approved' or 'rejected')
            notes: Optional notes from admin
        
        Returns:
            Boolean indicating success or failure
        """
        subject = f"Verification {status.capitalize()}"
        
        if status == 'approved':
            message = "Your identity verification has been approved. Your account is now fully verified."
        else:
            message = "Your identity verification has been rejected."
        
        # app/services/notification_service.py (continued)
        html_content = f"""
        <html>
        <body>
            <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;border:1px solid #e0e0e0;border-radius:5px;">
                <h2 style="color:#333;">Verification {status.capitalize()}</h2>
                <p>Hello {user.username},</p>
                <p>{message}</p>
                {f'<p><strong>Admin Notes:</strong> {notes}</p>' if notes else ''}
                <p style="margin-top:20px;">Thank you for using our platform.</p>
                <p style="margin-top:30px;font-size:12px;color:#777;">
                    This is an automated message. Please do not reply to this email.
                </p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Verification {status.capitalize()}
        
        Hello {user.username},
        
        {message}
        {f'Admin Notes: {notes}' if notes else ''}
        
        Thank you for using our platform.
        """
        
        # Send email
        email_success = NotificationService.send_email(
            user.email, 
            subject, 
            html_content, 
            text_content
        )
        
        # Send push notification
        push_success = NotificationService.send_push_notification(
            user.id,
            subject,
            message
        )
        
        return email_success and push_success
    
    @staticmethod
    def send_signal_notification(users, signal):
        """
        Send a notification about a new trading signal.
        
        Args:
            users: List of User objects to notify
            signal: TradeSignal object
        
        Returns:
            Number of successful notifications
        """
        subject = f"New Trading Signal: {signal.currency_pair} {signal.signal_type.upper()}"
        
        successful_count = 0
        
        for user in users:
            html_content = f"""
            <html>
            <body>
                <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;border:1px solid #e0e0e0;border-radius:5px;">
                    <h2 style="color:#333;">New Trading Signal</h2>
                    <p>Hello {user.username},</p>
                    <p>A new trading signal has been published:</p>
                    <div style="background-color:#f5f5f5;padding:15px;border-radius:5px;">
                        <p><strong>Pair:</strong> {signal.currency_pair}</p>
                        <p><strong>Type:</strong> {signal.signal_type.upper()}</p>
                        <p><strong>Entry Price:</strong> ${signal.entry_price}</p>
                        <p><strong>Target Price:</strong> ${signal.target_price}</p>
                        <p><strong>Stop Loss:</strong> ${signal.stop_loss}</p>
                        <p><strong>Leverage:</strong> {signal.leverage}x</p>
                        {f'<p><strong>Description:</strong> {signal.description}</p>' if signal.description else ''}
                    </div>
                    <p style="margin-top:20px;">Open the app to take action on this signal.</p>
                    <p style="margin-top:30px;font-size:12px;color:#777;">
                        This is an automated message. Please do not reply to this email.
                    </p>
                </div>
            </body>
            </html>
            """
            
            text_content = f"""
            New Trading Signal
            
            Hello {user.username},
            
            A new trading signal has been published:
            
            Pair: {signal.currency_pair}
            Type: {signal.signal_type.upper()}
            Entry Price: ${signal.entry_price}
            Target Price: ${signal.target_price}
            Stop Loss: ${signal.stop_loss}
            Leverage: {signal.leverage}x
            {f'Description: {signal.description}' if signal.description else ''}
            
            Open the app to take action on this signal.
            """
            
            # Send email
            email_success = NotificationService.send_email(
                user.email, 
                subject, 
                html_content, 
                text_content
            )
            
            # Send push notification
            push_success = NotificationService.send_push_notification(
                user.id,
                subject,
                f"New {signal.signal_type.upper()} signal for {signal.currency_pair} at ${signal.entry_price}"
            )
            
            if email_success and push_success:
                successful_count += 1
        
        return successful_count
    
    @staticmethod
    def send_announcement(users, announcement):
        """
        Send an announcement to users.
        
        Args:
            users: List of User objects to notify
            announcement: Announcement object
        
        Returns:
            Number of successful notifications
        """
        subject = announcement.title
        
        successful_count = 0
        
        for user in users:
            html_content = f"""
            <html>
            <body>
                <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;border:1px solid #e0e0e0;border-radius:5px;">
                    <h2 style="color:#333;">{announcement.title}</h2>
                    <p>Hello {user.username},</p>
                    <div style="background-color:#f5f5f5;padding:15px;border-radius:5px;">
                        {announcement.content}
                    </div>
                    <p style="margin-top:30px;font-size:12px;color:#777;">
                        This is an automated message. Please do not reply to this email.
                    </p>
                </div>
            </body>
            </html>
            """
            
            # Send email
            email_success = NotificationService.send_email(
                user.email, 
                subject, 
                html_content
            )
            
            # Send push notification
            push_success = NotificationService.send_push_notification(
                user.id,
                subject,
                announcement.content[:100] + ('...' if len(announcement.content) > 100 else '')
            )
            
            if email_success and push_success:
                successful_count += 1
        
        return successful_count
    
    @staticmethod
    def send_security_alert(user, action, ip_address, device_info, location=None):
        """
        Send a security alert for suspicious or important account activity.
        
        Args:
            user: User object
            action: Action that triggered the alert (login, password change, etc.)
            ip_address: IP address that performed the action
            device_info: Information about the device used
            location: Approximate location (optional)
        
        Returns:
            Boolean indicating success or failure
        """
        subject = f"Security Alert: {action}"
        
        html_content = f"""
        <html>
        <body>
            <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;border:1px solid #e0e0e0;border-radius:5px;">
                <h2 style="color:#333;">Security Alert</h2>
                <p>Hello {user.username},</p>
                <p>We detected the following activity on your account:</p>
                <div style="background-color:#f5f5f5;padding:15px;border-radius:5px;">
                    <p><strong>Action:</strong> {action}</p>
                    <p><strong>Time:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
                    <p><strong>IP Address:</strong> {ip_address}</p>
                    <p><strong>Device:</strong> {device_info}</p>
                    {f'<p><strong>Location:</strong> {location}</p>' if location else ''}
                </div>
                <p style="margin-top:20px;">If this was you, you can ignore this message. If you didn't perform this action, please secure your account immediately:</p>
                <ol style="margin-top:10px;">
                    <li>Change your password</li>
                    <li>Enable two-factor authentication if not already enabled</li>
                    <li>Contact our support team</li>
                </ol>
                <p style="margin-top:30px;font-size:12px;color:#777;">
                    This is an automated message. Please do not reply to this email.
                </p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Security Alert: {action}
        
        Hello {user.username},
        
        We detected the following activity on your account:
        
        Action: {action}
        Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
        IP Address: {ip_address}
        Device: {device_info}
        {f'Location: {location}' if location else ''}
        
        If this was you, you can ignore this message. If you didn't perform this action, please secure your account immediately:
        
        1. Change your password
        2. Enable two-factor authentication if not already enabled
        3. Contact our support team
        """
        
        # Send email (high priority)
        email_success = NotificationService.send_email(
            user.email, 
            subject, 
            html_content, 
            text_content
        )
        
        # Send SMS for critical security alerts
        sms_content = f"Security Alert: {action} detected on your account at {datetime.utcnow().strftime('%H:%M')} UTC. If this wasn't you, please secure your account immediately."
        sms_success = NotificationService.send_sms(user.phone, sms_content)
        
        # Send push notification
        push_success = NotificationService.send_push_notification(
            user.id,
            subject,
            f"{action} detected on your account. If this wasn't you, please secure your account immediately."
        )
        
        return email_success and sms_success and push_success
    
    @staticmethod
    def send_welcome_email(user):
        """
        Send a welcome email to a new user.
        
        Args:
            user: User object
        
        Returns:
            Boolean indicating success or failure
        """
        subject = f"Welcome to CryptoTrader, {user.username}!"
        
        html_content = f"""
        <html>
        <body>
            <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;border:1px solid #e0e0e0;border-radius:5px;">
                <h2 style="color:#333;">Welcome to CryptoTrader!</h2>
                <p>Hello {user.username},</p>
                <p>Thank you for joining CryptoTrader! We're excited to have you on board.</p>
                <p>Here's what you can do next:</p>
                <ul>
                    <li>Complete your profile</li>
                    <li>Verify your identity to unlock all features</li>
                    <li>Deposit funds to start trading</li>
                    <li>Explore our trading signals for guided trading</li>
                </ul>
                <p>If you have any questions, feel free to contact our support team.</p>
                <p style="margin-top:20px;">Happy trading!</p>
                <p>The CryptoTrader Team</p>
                <p style="margin-top:30px;font-size:12px;color:#777;">
                    This is an automated message. Please do not reply to this email.
                </p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Welcome to CryptoTrader, {user.username}!
        
        Hello {user.username},
        
        Thank you for joining CryptoTrader! We're excited to have you on board.
        
        Here's what you can do next:
        - Complete your profile
        - Verify your identity to unlock all features
        - Deposit funds to start trading
        - Explore our trading signals for guided trading
        
        If you have any questions, feel free to contact our support team.
        
        Happy trading!
        The CryptoTrader Team
        """
        
        # Send email
        return NotificationService.send_email(
            user.email, 
            subject, 
            html_content, 
            text_content
        )

# Convenience functions to simplify usage throughout the application

def send_otp_email(email, otp):
    """
    Send OTP via email.
    
    Args:
        email: Recipient email address
        otp: OTP code
    
    Returns:
        Boolean indicating success or failure
    """
    # Find user by email
    user = User.query.filter_by(email=email).first()
    if not user:
        return False
    
    return NotificationService.send_otp_notification(user, otp, method='email')

def send_otp_sms(phone, otp):
    """
    Send OTP via SMS.
    
    Args:
        phone: Recipient phone number
        otp: OTP code
    
    Returns:
        Boolean indicating success or failure
    """
    # Find user by phone
    user = User.query.filter_by(phone=phone).first()
    if not user:
        return False
    
    return NotificationService.send_otp_notification(user, otp, method='sms')

def send_verification_notification(user, status, notes=None):
    """
    Send verification status notification.
    
    Args:
        user: User object
        status: Verification status ('approved' or 'rejected')
        notes: Optional notes from admin
    
    Returns:
        Boolean indicating success or failure
    """
    return NotificationService.send_verification_notification(user, status, notes)

def send_transaction_notification(user, transaction):
    """
    Send transaction notification.
    
    Args:
        user: User object
        transaction: Transaction object
    
    Returns:
        Boolean indicating success or failure
    """
    return NotificationService.send_transaction_notification(user, transaction)

def send_signal_notification(users, signal):
    """
    Send trading signal notification.
    
    Args:
        users: List of User objects to notify
        signal: TradeSignal object
    
    Returns:
        Number of successful notifications
    """
    return NotificationService.send_signal_notification(users, signal)

def send_announcement(users, announcement):
    """
    Send announcement notification.
    
    Args:
        users: List of User objects to notify
        announcement: Announcement object
    
    Returns:
        Number of successful notifications
    """
    return NotificationService.send_announcement(users, announcement)

def send_security_alert(user, action, ip_address, device_info, location=None):
    """
    Send security alert notification.
    
    Args:
        user: User object
        action: Action that triggered the alert
        ip_address: IP address that performed the action
        device_info: Information about the device used
        location: Approximate location (optional)
    
    Returns:
        Boolean indicating success or failure
    """
    return NotificationService.send_security_alert(user, action, ip_address, device_info, location)

def send_welcome_email(user):
    """
    Send welcome email to new user.
    
    Args:
        user: User object
    
    Returns:
        Boolean indicating success or failure
    """
    return NotificationService.send_welcome_email(user)
