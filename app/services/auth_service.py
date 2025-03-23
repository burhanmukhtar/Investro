# app/services/auth_service.py
import random
import string
from datetime import datetime, timedelta
import threading
from app import db
from app.models.user import User
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import Config
import logging
import time
from email.mime.image import MIMEImage

logger = logging.getLogger(__name__)

def generate_otp():
    """Generate a 6-digit OTP."""
    return ''.join(random.choices(string.digits, k=6))

def send_otp_email(email, otp):
    """Send OTP via email asynchronously."""
    thread = threading.Thread(target=_send_otp_email_task, args=(email, otp))
    thread.daemon = True
    thread.start()
    return True

def _send_otp_email_task(email, otp):
    """Background task to send OTP email with improved error handling and Investro branding."""
    try:
        # Format the OTP for display
        otp_string = str(otp)
        
        # Current timestamp for a dynamic countdown start
        current_timestamp = int(time.time())
        expiry_timestamp = current_timestamp + 300  # 5 minutes in seconds
        
        # Email body with Investro branding
        body = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
    <meta name="color-scheme" content="light dark">
    <meta name="supported-color-schemes" content="light dark">
    <title>Your Investro Verification Code</title>
    <style>
        /* Base styles with proper light and dark mode support */
        @media (prefers-color-scheme: light) {{
            :root {{
                color-scheme: light;
                --text-color: #333333;
                --background-color: #ffffff;
                --container-bg: #ffffff;
                --header-bg: #f8f8f8;
                --header-text: #333333;
                --header-accent: #9370DB;
                --content-bg: #ffffff;
                --otp-container-bg: #f2f2f2;
                --otp-container-border: #dddddd;
                --otp-text: #333333;
                --footer-bg: #f8f8f8;
                --footer-text: #333333;
                --footer-link: #9370DB;
                --countdown-bg: #e0e0e0;
                --countdown-fill: linear-gradient(90deg, #7B68EE, #9370DB);
                --button-bg: #0088cc;
                --button-text: #ffffff;
                --main-border: #e0e0e0;
            }}
        }}
        
        @media (prefers-color-scheme: dark) {{
            :root {{
                color-scheme: dark;
                --text-color: #f7f7f7;
                --background-color: #121212;
                --container-bg: #1E1E1E;
                --header-bg: #252525;
                --header-text: #f7f7f7;
                --header-accent: #9370DB;
                --content-bg: #1E1E1E;
                --otp-container-bg: #2A2A2A;
                --otp-container-border: #444444;
                --otp-text: #f7f7f7;
                --footer-bg: #252525;
                --footer-text: #f7f7f7;
                --footer-link: #9370DB;
                --countdown-bg: #333333;
                --countdown-fill: linear-gradient(90deg, #7B68EE, #9370DB);
                --button-bg: #0088cc;
                --button-text: #ffffff;
                --main-border: #444444;
            }}
        }}
        
        body {{
            margin: 0;
            padding: 0;
            font-family: 'Segoe UI', Arial, sans-serif;
            background-color: var(--background-color);
            color: var(--text-color);
        }}
        
        .container {{
            background-color: var(--container-bg);
        }}
        
        .header {{
            background-color: var(--header-bg);
            color: var(--header-text);
        }}
        
        .header-accent {{
            color: var(--header-accent);
        }}
        
        .content {{
            background-color: var(--content-bg);
            color: var(--text-color);
        }}
        
        .otp-container {{
            background-color: var(--otp-container-bg);
            border: 1px solid var(--otp-container-border);
        }}
        
        .otp-code {{
            color: var(--otp-text);
        }}
        
        .footer {{
            background-color: var(--footer-bg);
            color: var(--footer-text);
            border-top: 1px solid var(--main-border);
        }}
        
        .footer-link {{
            color: var(--footer-link);
        }}
        
        .countdown-bar-bg {{
            background-color: var(--countdown-bg);
        }}
        
        .countdown-bar {{
            background: var(--countdown-fill);
            animation: countdown 300s linear forwards;
        }}
        
        @keyframes countdown {{
            0% {{
                width: 100%;
            }}
            100% {{
                width: 0%;
            }}
        }}
        
        #countdown-timer {{
            font-family: 'Courier New', monospace;
            font-weight: bold;
        }}
        
        /* JavaScript countdown fallback */
        .countdown-js {{
            display: inline-block;
            min-width: 50px;
            text-align: center;
        }}
    </style>
    <script type="text/javascript">
        window.onload = function() {{
            var countDownDate = new Date().getTime() + (5 * 60 * 1000); // 5 minutes
            var timerElement = document.getElementById('countdown-timer');
            
            // Update the countdown every second
            var x = setInterval(function() {{
                var now = new Date().getTime();
                var distance = countDownDate - now;
                
                var minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
                var seconds = Math.floor((distance % (1000 * 60)) / 1000);
                
                // Format the display with leading zeros
                minutes = (minutes < 10) ? "0" + minutes : minutes;
                seconds = (seconds < 10) ? "0" + seconds : seconds;
                
                // Display the result
                timerElement.innerHTML = minutes + ":" + seconds;
                
                // If the countdown is finished
                if (distance < 0) {{
                    clearInterval(x);
                    timerElement.innerHTML = "00:00";
                }}
            }}, 1000);
        }};
    </script>
</head>
<body>
    <!-- Preheader text -->
    <div style="display: none; max-height: 0px; overflow: hidden;">
        Your Investro verification code is ready - valid for 5 minutes only
    </div>
    
    <!-- Container -->
    <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="border-collapse: collapse;">
        <tr>
            <td align="center" style="padding: 10px 0;">
                <!-- Inner container -->
                <table role="presentation" class="container" border="0" cellpadding="0" cellspacing="0" width="100%" style="border-collapse: collapse; max-width: 600px; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);">
                    <!-- Top accent bar -->
                    <tr>
                        <td style="height: 6px; background: linear-gradient(90deg, #7B68EE, #9370DB, #483D8B);"></td>
                    </tr>
                    
                    <!-- Header with logo -->
                    <tr>
                        <td class="header" style="padding: 20px 30px;">
                            <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="border-collapse: collapse;">
                                <tr>
                                    <td width="30%" style="text-align: left; vertical-align: middle;">
                                        <img src="cid:logo" alt="Investro" width="100" style="display: block; border: 0; height: auto; max-width: 100px;">
                                    </td>
                                    <td width="70%" style="text-align: right; vertical-align: middle;">
                                        <p class="header-accent" style="margin: 0; font-family: 'Segoe UI', Arial, sans-serif; font-size: 14px; font-weight: bold;">ACCOUNT SECURITY</p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Main content section -->
                    <tr>
                        <td class="content" style="padding: 30px 30px 20px 30px;">
                            <h1 style="margin: 0 0 20px 0; font-family: 'Segoe UI', Arial, sans-serif; font-size: 24px; font-weight: bold; text-align: left;">Verify Your Account</h1>
                            
                            <p style="margin: 0 0 20px 0; font-family: 'Segoe UI', Arial, sans-serif; font-size: 16px; line-height: 1.5; text-align: left;">We've received a request to access your Investro account. Please use the verification code below to complete the authentication process:</p>
                            
                            <!-- OTP Container -->
                            <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="border-collapse: collapse; margin: 30px 0;">
                                <tr>
                                    <td align="center">
                                        <!-- OTP box that's easy to copy -->
                                        <div class="otp-container" style="display: inline-block; padding: 15px 25px; border-radius: 8px; margin-bottom: 20px;">
                                            <span class="otp-code" style="font-family: 'Courier New', monospace; font-size: 28px; font-weight: bold; letter-spacing: 5px; user-select: all; -webkit-user-select: all; -moz-user-select: all; -ms-user-select: all; cursor: text;">{otp_string}</span>
                                        </div>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding: 0;">
                                        <!-- Visual countdown -->
                                        <div class="countdown-bar-bg" style="height: 6px; width: 100%; border-radius: 3px; position: relative; overflow: hidden;">
                                            <div class="countdown-bar" style="height: 6px; width: 100%; border-radius: 3px; animation: countdown 300s linear forwards;"></div>
                                        </div>
                                        <p style="margin: 8px 0 0 0; font-family: 'Segoe UI', Arial, sans-serif; font-size: 12px; text-align: center;">
                                            Code expires in <span id="countdown-timer" class="countdown-js">05:00</span>
                                        </p>
                                    </td>
                                </tr>
                            </table>
                            
                            <!-- Security notice -->
                            <p style="margin: 25px 0 0 0; font-family: 'Segoe UI', Arial, sans-serif; font-size: 14px; line-height: 1.5;">If you did not request this code, please <a href="https://theinvestro.io/security.html" style="color: var(--footer-link); text-decoration: underline;">secure your account</a> immediately.</p>
                            
                            <!-- Telegram link -->
                            <p style="margin: 25px 0 0 0; font-family: 'Segoe UI', Arial, sans-serif; font-size: 14px; line-height: 1.5; text-align: center;">
                                <a href="https://t.me/theinvestr0" style="display: inline-block; padding: 10px 20px; background-color: #0088cc; color: #ffffff; text-decoration: none; border-radius: 4px; font-weight: bold;">Join Our Telegram Group</a>
                            </p>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td class="footer" style="padding: 20px 30px;">
                            <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="border-collapse: collapse;">
                                <tr>
                                    <td style="text-align: center;">
                                        <p style="margin: 0 0 10px 0; font-family: 'Segoe UI', Arial, sans-serif; font-size: 12px;">© 2025 Investro Inc. All rights reserved.</p>
                                        <p style="margin: 0 0 10px 0; font-family: 'Segoe UI', Arial, sans-serif; font-size: 12px;">
                                            <a href="https://theinvestro.io/terms.html" class="footer-link" style="text-decoration: underline; margin: 0 10px;">Terms</a>
                                            <a href="https://theinvestro.io/privacy.html" class="footer-link" style="text-decoration: underline; margin: 0 10px;">Privacy</a>
                                        </p>
                                        <p style="margin: 0; font-family: 'Segoe UI', Arial, sans-serif; font-size: 12px;">
                                            <a href="https://theinvestro.io/unsubscribe.html" class="footer-link" style="text-decoration: underline;">Unsubscribe</a>
                                        </p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
        """
        
        # Setup email message with proper structure for embedded images
        message = MIMEMultipart('related')
        message['From'] = Config.MAIL_USERNAME
        message['To'] = email
        message['Subject'] = 'Your Investro Verification Code'
        
        # Create alternative part for HTML content
        msgAlternative = MIMEMultipart('alternative')
        message.attach(msgAlternative)
        
        # Attach HTML content
        msgAlternative.attach(MIMEText(body, 'html'))
        
        # Fetch and attach logo image 
        try:
            import urllib.request
            with urllib.request.urlopen('https://theinvestro.io/Assets/logo.png') as response:
                logo_data = response.read()
                logo_image = MIMEImage(logo_data)
                logo_image.add_header('Content-ID', '<logo>')
                logo_image.add_header('Content-Disposition', 'inline', filename='logo.png')
                message.attach(logo_image)
                logger.info("Logo image attached successfully")
        except Exception as e:
            logger.warning(f"Could not attach logo image: {e}")
        
        # Log connection attempt for debugging
        logger.info(f"Attempting to connect to SMTP server {Config.MAIL_SERVER}:{Config.MAIL_PORT}")
        
        try:
            # Choose the correct SMTP class based on SSL/TLS settings
            if hasattr(Config, 'MAIL_USE_SSL') and Config.MAIL_USE_SSL:
                server = smtplib.SMTP_SSL(Config.MAIL_SERVER, Config.MAIL_PORT, timeout=30)
                logger.info("Using SMTP_SSL connection")
            else:
                server = smtplib.SMTP(Config.MAIL_SERVER, Config.MAIL_PORT, timeout=30)
                logger.info("Using standard SMTP connection")
                
                # Start TLS if configured
                if hasattr(Config, 'MAIL_USE_TLS') and Config.MAIL_USE_TLS:
                    server.starttls()
                    logger.info("TLS connection established")
            
            # Login if credentials are provided
            if Config.MAIL_USERNAME and Config.MAIL_PASSWORD:
                logger.info(f"Attempting login with username: {Config.MAIL_USERNAME}")
                server.login(Config.MAIL_USERNAME, Config.MAIL_PASSWORD)
                logger.info("Login successful")
            
            # Send email
            logger.info(f"Sending email to {email}")
            server.send_message(message)
            server.quit()
            
            logger.info(f"OTP email sent successfully to {email}")
            return True
            
        except smtplib.SMTPConnectError as connect_error:
            logger.error(f"Failed to connect to SMTP server: {connect_error}")
            # Fall back to alternative method if available
            return _send_email_fallback(email, otp)
            
        except smtplib.SMTPServerDisconnected as disconnect_error:
            logger.error(f"SMTP server disconnected: {disconnect_error}")
            return _send_email_fallback(email, otp)
            
        except smtplib.SMTPAuthenticationError as auth_error:
            logger.error(f"SMTP authentication failed: {auth_error}")
            return _send_email_fallback(email, otp)
            
        except smtplib.SMTPException as smtp_error:
            logger.error(f"SMTP error: {smtp_error}")
            return _send_email_fallback(email, otp)
            
        except TimeoutError:
            logger.error("SMTP connection timed out")
            return _send_email_fallback(email, otp)
            
        except OSError as os_error:
            logger.error(f"OS error during email sending: {os_error}")
            return _send_email_fallback(email, otp)
            
    except Exception as e:
        logger.error(f"Unexpected error sending OTP email: {e}")
        return False


def _send_email_fallback(email, otp):
    """Fallback method for sending OTP emails if SMTP fails."""
    try:
        # If you have an alternative email service, use it here
        # For example, you might use a third-party API like SendGrid, Mailgun, etc.
        
        # For now, just log that we would use a fallback
        logger.info(f"Would use fallback email service to send OTP to {email}")
        
        # If you're in development mode, log the OTP for testing
        if hasattr(Config, 'ENVIRONMENT') and Config.ENVIRONMENT == 'development':
            logger.info(f"DEVELOPMENT MODE: OTP for {email} is {otp}")
            return True
            
        # TODO: Implement actual fallback email sending
        # Example: return send_via_sendgrid(email, otp)
        
        return False
    except Exception as e:
        logger.error(f"Fallback email delivery also failed: {e}")
        return False

def verify_otp(user_id, otp):
    """Verify the OTP for a user."""
    user = User.query.get(user_id)
    
    if not user:
        return False
    
    if user.otp == otp and datetime.utcnow() <= user.otp_expiry:
        user.otp = None
        user.otp_expiry = None
        db.session.commit()
        return True
    
    # In development mode, check if entered OTP is "000000" as a backup
    if hasattr(Config, 'ENVIRONMENT') and Config.ENVIRONMENT == 'development':
        if otp == "000000":
            logger.warning(f"DEVELOPMENT MODE: Using backup OTP code for user {user_id}")
            user.otp = None
            user.otp_expiry = None
            db.session.commit()
            return True
    
    return False

def test_email_configuration():
    """Test SMTP email configuration and return detailed diagnostics."""
    results = {
        "success": False,
        "connection": False,
        "authentication": False,
        "sending": False,
        "errors": []
    }
    
    try:
        # 1. Test basic connection
        logger.info(f"Testing connection to SMTP server {Config.MAIL_SERVER}:{Config.MAIL_PORT}")
        try:
            # Choose the correct SMTP class based on SSL/TLS settings
            if hasattr(Config, 'MAIL_USE_SSL') and Config.MAIL_USE_SSL:
                server = smtplib.SMTP_SSL(Config.MAIL_SERVER, Config.MAIL_PORT, timeout=10)
                logger.info("Using SMTP_SSL connection")
            else:
                server = smtplib.SMTP(Config.MAIL_SERVER, Config.MAIL_PORT, timeout=10)
                logger.info("Using standard SMTP connection")
                
                # Start TLS if configured
                if hasattr(Config, 'MAIL_USE_TLS') and Config.MAIL_USE_TLS:
                    server.starttls()
                    logger.info("TLS connection established")
            
            results["connection"] = True
            logger.info("Connection established successfully")
            
            # 3. Test authentication if credentials are provided
            if Config.MAIL_USERNAME and Config.MAIL_PASSWORD:
                logger.info(f"Testing authentication with username: {Config.MAIL_USERNAME}")
                server.login(Config.MAIL_USERNAME, Config.MAIL_PASSWORD)
                results["authentication"] = True
                logger.info("Authentication successful")
                
                # 4. Optional: Test sending a message
                # Create a simple test message
                test_message = MIMEText("This is a test email from your application.")
                test_message["Subject"] = "SMTP Test"
                test_message["From"] = Config.MAIL_USERNAME
                test_message["To"] = Config.MAIL_USERNAME  # Send to self for testing
                
                # Just verify connection is working without actually sending
                # server.sendmail(Config.MAIL_USERNAME, Config.MAIL_USERNAME, test_message.as_string())
                # results["sending"] = True
                # logger.info("Test email sent successfully")
                
                # Since we got to authentication, mark the test as successful
                results["success"] = True
            
            server.quit()
            
        except smtplib.SMTPConnectError as e:
            results["errors"].append(f"Connection error: {str(e)}")
            logger.error(f"SMTP connection failed: {e}")
        except smtplib.SMTPAuthenticationError as e:
            results["errors"].append(f"Authentication error: {str(e)}")
            logger.error(f"SMTP authentication failed: {e}")
        except smtplib.SMTPException as e:
            results["errors"].append(f"SMTP error: {str(e)}")
            logger.error(f"SMTP error: {e}")
        except TimeoutError:
            results["errors"].append("Connection timed out")
            logger.error("SMTP connection timed out")
        except OSError as e:
            results["errors"].append(f"OS error: {str(e)}")
            logger.error(f"OS error during SMTP test: {e}")
        except Exception as e:
            results["errors"].append(f"Unexpected error: {str(e)}")
            logger.error(f"Unexpected error during SMTP test: {e}")
            
    except Exception as e:
        results["errors"].append(f"Setup error: {str(e)}")
        logger.error(f"Error setting up SMTP test: {e}")
        
    return results

def register_user(username, email, phone, password, referral_code=None):
    """Register a new user."""
    # Check if username, email, or phone already exists
    if User.query.filter_by(username=username).first():
        return None, "Username already exists."
    
    if User.query.filter_by(email=email).first():
        return None, "Email already registered."
    
    if User.query.filter_by(phone=phone).first():
        return None, "Phone number already registered."
    
    # Check referral code if provided
    referred_by = None
    if referral_code:
        referring_user = User.query.filter_by(referral_code=referral_code).first()
        if referring_user:
            referred_by = referral_code
        else:
            return None, "Invalid referral code."
    
    # Create new user
    user = User(username=username, email=email, phone=phone, password=password, referred_by=referred_by)
    db.session.add(user)
    db.session.commit()
    
    return user, "User registered successfully."