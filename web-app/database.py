"""
Database Configuration and Models for Eye Strain Monitoring App
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class User(db.Model):
    """User account model"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(20), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), nullable=False)
    mobile = db.Column(db.String(15), nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    failed_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime, nullable=True)
    
    # Profile fields
    age = db.Column(db.Integer, nullable=True)
    gender = db.Column(db.String(20), nullable=True)  # male, female, other
    uses_glasses = db.Column(db.Boolean, nullable=True)
    glasses_power_left = db.Column(db.String(20), nullable=True)
    glasses_power_right = db.Column(db.String(20), nullable=True)
    profile_completed = db.Column(db.Boolean, default=False)
    
    # Relationships
    reports = db.relationship('EyeStrainReport', backref='user', lazy='dynamic')
    otps = db.relationship('OTP', backref='user', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': self.id,
            'full_name': self.full_name,
            'username': self.username,
            'email': self.email,
            'mobile': self.mobile,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_active': self.is_active,
            'age': self.age,
            'gender': self.gender,
            'uses_glasses': self.uses_glasses,
            'glasses_power_left': self.glasses_power_left,
            'glasses_power_right': self.glasses_power_right,
            'profile_completed': self.profile_completed
        }


class EyeStrainReport(db.Model):
    """Eye strain report model for storing user-specific metrics"""
    __tablename__ = 'eye_strain_reports'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    session_id = db.Column(db.String(36), nullable=True, index=True)  # UUID for grouping session reports
    blinks_per_min = db.Column(db.Float, default=0.0)
    perclos = db.Column(db.Float, default=0.0)
    avg_ear = db.Column(db.Float, default=0.0)
    avg_blink_duration_ms = db.Column(db.Float, default=0.0)
    strain_level = db.Column(db.String(20), default='Unknown')
    session_duration_seconds = db.Column(db.Integer, default=0)
    total_blinks = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'blinks_per_min': self.blinks_per_min,
            'perclos': self.perclos,
            'avg_ear': self.avg_ear,
            'avg_blink_duration_ms': self.avg_blink_duration_ms,
            'strain_level': self.strain_level,
            'session_duration_seconds': self.session_duration_seconds,
            'total_blinks': self.total_blinks,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class OTP(db.Model):
    """One-Time Password model for 2FA"""
    __tablename__ = 'otps'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    code = db.Column(db.String(6), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def is_valid(self):
        """Check if OTP is valid (not expired and not used)"""
        return not self.is_used and datetime.utcnow() < self.expires_at


class LoginAttempt(db.Model):
    """Track login attempts for brute force protection"""
    __tablename__ = 'login_attempts'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, index=True)
    ip_address = db.Column(db.String(45), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    success = db.Column(db.Boolean, default=False)


def init_db(app):
    """Initialize database with the Flask app"""
    db.init_app(app)
    with app.app_context():
        db.create_all()
    return db
