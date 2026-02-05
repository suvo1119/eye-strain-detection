"""
Authentication Routes for Eye Strain Monitoring App
Handles user registration, login with OTP, and session management
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, create_refresh_token, jwt_required,
    get_jwt_identity, get_jwt
)
from datetime import datetime, timedelta
import bcrypt
import secrets
import re
from dotenv import load_dotenv

load_dotenv()

from database import db, User, OTP, LoginAttempt
import os

# Optional Twilio SMS support. If `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and
# `TWILIO_FROM_NUMBER` are set in the environment and `twilio` is installed,
# the server will send OTPs via SMS. Otherwise the OTP is printed to console
# (useful for local testing).
try:
    from twilio.rest import Client as TwilioClient
except Exception:
    TwilioClient = None

try:
    import requests
except Exception:
    requests = None

try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail
except Exception:
    SendGridAPIClient = None
    Mail = None


def send_otp_via_msg91(mobile, code):
    """Send OTP via MSG91 (India) using sendhttp.php endpoint. Requires MSG91_AUTHKEY and optionally MSG91_SENDER_ID."""
    api_key = os.environ.get('MSG91_AUTHKEY') or os.environ.get('MSG91_API_KEY')
    sender = os.environ.get('MSG91_SENDER_ID', 'MSGIND')
    if not (api_key and requests):
        return False

    try:
        numbers = re.sub(r'\D', '', mobile)
        # If only 10 digits provided, assume India and prefix 91
        if len(numbers) == 10:
            numbers = '91' + numbers
        message = f'Your verification code is: {code}'
        params = {
            'authkey': api_key,
            'mobiles': numbers,
            'message': message,
            'sender': sender,
            'route': '4',
            'country': '91'
        }
        resp = requests.get('https://api.msg91.com/api/sendhttp.php', params=params, timeout=10)
        return resp.status_code == 200 and resp.text.strip() != ''
    except Exception as e:
        print(f"Failed to send OTP via MSG91: {e}")
        return False


def send_otp_via_fast2sms(mobile, code):
    """Send OTP via Fast2SMS (India). Requires FAST2SMS_API_KEY env var."""
    api_key = os.environ.get('FAST2SMS_API_KEY')
    if not (api_key and requests):
        return False

    try:
        url = 'https://www.fast2sms.com/dev/bulk'
        payload = {
            'sender_id': 'FSTSMS',
            'message': f'Your verification code is: {code}',
            'language': 'english',
            'route': 'p',
            'numbers': re.sub(r'\D', '', mobile)
        }
        headers = {
            'authorization': api_key,
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        resp = requests.post(url, data=payload, headers=headers, timeout=10)
        return resp.status_code == 200 and ('OK' in resp.text or 'success' in resp.text.lower())
    except Exception as e:
        print(f"Failed to send OTP via Fast2SMS: {e}")
        return False


def send_otp_via_sendgrid(email, code):
    """Send OTP via SendGrid. Requires SENDGRID_API_KEY and EMAIL_FROM env vars."""
    api_key = os.environ.get('SENDGRID_API_KEY')
    email_from = os.environ.get('EMAIL_FROM')
    if not api_key:
        return False

    # Prefer sendgrid package if available
    try:
        if SendGridAPIClient and Mail and email_from:
            message = Mail(
                from_email=email_from,
                to_emails=email,
                subject='Your verification code',
                plain_text_content=f'Your verification code is: {code}'
            )
            sg = SendGridAPIClient(api_key)
            resp = sg.send(message)
            return 200 <= resp.status_code < 300
        elif requests and api_key and email_from:
            url = 'https://api.sendgrid.com/v3/mail/send'
            payload = {
                'personalizations': [{ 'to': [{ 'email': email }] }],
                'from': { 'email': email_from },
                'subject': 'Your verification code',
                'content': [{ 'type': 'text/plain', 'value': f'Your verification code is: {code}' }]
            }
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            resp = requests.post(url, json=payload, headers=headers, timeout=10)
            return 200 <= resp.status_code < 300
    except Exception as e:
        print(f"Failed to send OTP via SendGrid: {e}")
        return False
    return False


def send_otp_via_twilio(mobile, code):
    """Attempt to send OTP via Twilio. Returns True on success."""
    sid = os.environ.get('TWILIO_ACCOUNT_SID')
    token = os.environ.get('TWILIO_AUTH_TOKEN')
    from_number = os.environ.get('TWILIO_FROM_NUMBER')

    if not (sid and token and from_number and TwilioClient):
        return False

    try:
        client = TwilioClient(sid, token)
        # Ensure mobile is in E.164 format (caller must provide correct format)
        message = client.messages.create(
            body=f"Your verification code is: {code}",
            from_=from_number,
            to=mobile
        )
        return True
    except Exception as e:
        print(f"Failed to send OTP via Twilio: {e}")
        return False


def send_otp_via_smtp(email, code):
    """Send OTP via SMTP. Requires SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, EMAIL_FROM env vars."""
    host = os.environ.get('SMTP_HOST')
    port = int(os.environ.get('SMTP_PORT', '587'))
    user = os.environ.get('SMTP_USER')
    password = os.environ.get('SMTP_PASSWORD')
    email_from = os.environ.get('EMAIL_FROM')

    if not (host and port and user and password and email_from):
        return False

    try:
        import smtplib
        from email.message import EmailMessage

        msg = EmailMessage()
        msg['Subject'] = 'Your verification code'
        msg['From'] = email_from
        msg['To'] = email
        msg.set_content(f'Your verification code is: {code}')

        # Use STARTTLS
        with smtplib.SMTP(host, port, timeout=10) as server:
            server.ehlo()
            if port == 587:
                server.starttls()
            server.login(user, password)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Failed to send OTP via SMTP: {e}")
        return False

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# Configuration
OTP_EXPIRY_MINUTES = 5
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_mobile(mobile):
    """Validate mobile number (at least 10 digits)"""
    digits = re.sub(r'\D', '', mobile)
    return len(digits) >= 10


def validate_username(username):
    """Validate username format (3-20 chars, alphanumeric + underscore)"""
    pattern = r'^[a-zA-Z0-9_]{3,20}$'
    return bool(re.match(pattern, username))


def hash_password(password):
    """Hash password using bcrypt"""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(password, password_hash):
    """Verify password against hash"""
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))


def generate_otp():
    """Generate a 6-digit OTP"""
    return ''.join([str(secrets.randbelow(10)) for _ in range(6)])


def is_account_locked(user):
    """Check if user account is locked"""
    if user.locked_until and datetime.utcnow() < user.locked_until:
        return True
    # Reset failed attempts if lockout has expired
    if user.locked_until and datetime.utcnow() >= user.locked_until:
        user.failed_attempts = 0
        user.locked_until = None
        db.session.commit()
    return False


def record_login_attempt(username, ip_address, success):
    """Record a login attempt"""
    attempt = LoginAttempt(
        username=username,
        ip_address=ip_address,
        success=success
    )
    db.session.add(attempt)
    db.session.commit()


@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    data = request.get_json()
    # For simplified auth we require only a unique user_id and password.
    # Support both `user_id` (preferred) and legacy `username` keys.
    required_fields = ['password', 'confirm_password']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f'{field.replace("_", " ").title()} is required'}), 400

    full_name = data.get('full_name', '').strip()
    identifier = (data.get('user_id') or data.get('username') or '').strip()
    if not identifier:
        return jsonify({'error': 'User ID is required'}), 400
    username = identifier.lower()
    email = data.get('email', '').strip().lower()
    mobile = data.get('mobile', '').strip()
    password = data['password']
    confirm_password = data['confirm_password']
    
    # Validate user id format
    if not validate_username(username):
        return jsonify({'error': 'User ID must be 3-20 characters, alphanumeric and underscores only'}), 400

    # Check user id uniqueness
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'User ID already taken'}), 400
    
    # Email and mobile are optional now; validate if provided
    if email and not validate_email(email):
        return jsonify({'error': 'Invalid email format'}), 400

    if mobile and not validate_mobile(mobile):
        return jsonify({'error': 'Mobile number must have at least 10 digits'}), 400
    
    # Validate password
    if len(password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400
    
    # Confirm password match
    if password != confirm_password:
        return jsonify({'error': 'Passwords do not match'}), 400
    
    # Create user
    user = User(
        full_name=full_name,
        username=username,
        email=email or '',
        mobile=mobile or '',
        password_hash=hash_password(password)
    )
    
    db.session.add(user)
    db.session.commit()
    
    # Generate tokens for auto-login after registration
    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))
    
    return jsonify({
        'message': 'Registration successful',
        'user': user.to_dict(),
        'access_token': access_token,
        'refresh_token': refresh_token
    }), 201


@auth_bp.route('/check-username/<username>', methods=['GET'])
def check_username(username):
    """Check if username is available"""
    # This endpoint keeps the legacy name `check-username` but checks the
    # `user id` value for availability.
    username = username.strip().lower()

    if not validate_username(username):
        return jsonify({'available': False, 'error': 'Invalid user id format'}), 200

    exists = User.query.filter_by(username=username).first() is not None
    return jsonify({'available': not exists}), 200


@auth_bp.route('/login', methods=['POST'])
def login():
    """Login step 1: Validate credentials and send OTP"""
    data = request.get_json()
    # Accept `user_id` or legacy `username` in the request body.
    username = (data.get('user_id') or data.get('username') or '').strip().lower()
    password = data.get('password', '')
    ip_address = request.remote_addr
    
    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400
    
    user = User.query.filter_by(username=username).first()
    
    if not user:
        record_login_attempt(username, ip_address, False)
        return jsonify({'error': 'Invalid user id or password'}), 401
    
    # Check if account is locked
    if is_account_locked(user):
        remaining = (user.locked_until - datetime.utcnow()).seconds // 60
        return jsonify({'error': f'Account locked. Try again in {remaining + 1} minutes'}), 403
    
    # Verify password
    if not verify_password(password, user.password_hash):
        user.failed_attempts += 1
        if user.failed_attempts >= MAX_LOGIN_ATTEMPTS:
            user.locked_until = datetime.utcnow() + timedelta(minutes=LOCKOUT_MINUTES)
        db.session.commit()
        record_login_attempt(username, ip_address, False)
        return jsonify({'error': 'Invalid user id or password'}), 401
    # Successful login (no OTP). Reset failures and return tokens.
    user.failed_attempts = 0
    user.locked_until = None
    db.session.commit()
    record_login_attempt(user.username, ip_address, True)

    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))

    return jsonify({
        'message': 'Login successful',
        'user': user.to_dict(),
        'access_token': access_token,
        'refresh_token': refresh_token
    }), 200


@auth_bp.route('/verify-otp', methods=['POST'])
def verify_otp():
    """OTP flow removed — endpoint disabled."""
    return jsonify({'error': 'OTP flow disabled. Use username/password login.'}), 410


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Refresh access token"""
    identity = get_jwt_identity()
    access_token = create_access_token(identity=identity)
    return jsonify({'access_token': access_token}), 200


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Get current user profile"""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({'user': user.to_dict()}), 200


@auth_bp.route('/profile', methods=['POST'])
@jwt_required()
def update_profile():
    """Update user profile with questionnaire data"""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json()
    
    # Validate age
    age = data.get('age')
    if age is not None:
        try:
            age = int(age)
            if age < 5 or age > 120:
                return jsonify({'error': 'Age must be between 5 and 120'}), 400
            user.age = age
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid age format'}), 400
    
    # Validate gender
    gender = data.get('gender')
    if gender:
        if gender not in ['male', 'female', 'other']:
            return jsonify({'error': 'Gender must be male, female, or other'}), 400
        user.gender = gender
    
    # Handle glasses info
    uses_glasses = data.get('uses_glasses')
    if uses_glasses is not None:
        user.uses_glasses = bool(uses_glasses)
        if user.uses_glasses:
            user.glasses_power_left = data.get('glasses_power_left', '')
            user.glasses_power_right = data.get('glasses_power_right', '')
        else:
            user.glasses_power_left = None
            user.glasses_power_right = None
    
    # Mark profile as completed
    user.profile_completed = True
    
    db.session.commit()
    
    return jsonify({
        'message': 'Profile updated successfully',
        'user': user.to_dict()
    }), 200


@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """Logout user (client should discard tokens)"""
    # In a production app, you'd add the token to a blocklist
    return jsonify({'message': 'Logged out successfully'}), 200
