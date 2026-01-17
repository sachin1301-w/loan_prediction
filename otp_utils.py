import random
import string
from datetime import datetime, timedelta, timezone
from models import OTP, db


def generate_otp():
    """Generate a 6-digit OTP"""
    return ''.join(random.choices(string.digits, k=6))


def create_otp(email, otp_type='login'):
    """Create and store OTP in database"""
    # Delete old OTPs for this email
    OTP.query.filter_by(email=email, is_used=False).delete()
    
    otp_code = generate_otp()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    
    new_otp = OTP(
        email=email,
        otp_code=otp_code,
        otp_type=otp_type,
        expires_at=expires_at
    )
    
    db.session.add(new_otp)
    db.session.commit()
    
    return otp_code


def verify_otp(email, otp_code, otp_type='login'):
    """Verify OTP"""
    otp_record = OTP.query.filter_by(
        email=email,
        otp_code=otp_code,
        otp_type=otp_type,
        is_used=False
    ).first()
    
    if not otp_record:
        return False, "Invalid OTP"
    
    if datetime.now(timezone.utc) > otp_record.expires_at:
        return False, "OTP has expired"
    
    # Mark OTP as used
    otp_record.is_used = True
    db.session.commit()
    
    return True, "OTP verified successfully"


def send_otp_email(email, otp_code, purpose="login"):
    """
    Display OTP in console with clear formatting for user visibility
    """
    import sys
    # Force flush to ensure output appears immediately
    sys.stdout.flush()
    sys.stderr.flush()
    
    # Display OTP in console with visible formatting
    message = f"""
{'='*70}
    
    🔐 LOAN PREDICTION SYSTEM - OTP VERIFICATION
    
    Email: {email}
    Purpose: {purpose.upper()}
    
    ╔═══════════════════════════════════════════╗
    ║                                           ║
    ║          YOUR OTP CODE: {otp_code}          ║
    ║                                           ║
    ╚═══════════════════════════════════════════╝
    
    ⏰ This OTP is valid for 10 minutes
    🔒 Do not share this code with anyone
    
{'='*70}
"""
    print(message, flush=True)
    
    # Also log to stderr for better visibility in different terminal modes
    print(f"\n⚡ OTP GENERATED: {otp_code} for {email}\n", file=sys.stderr, flush=True)
    
    return True
