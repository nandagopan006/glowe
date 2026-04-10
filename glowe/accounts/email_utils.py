import random
import string
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.conf import settings
from email.mime.image import MIMEImage
import os
from django.utils import timezone
from datetime import timedelta

def generate_otp(length=4):

    return ''.join(random.choices(string.digits, k=length))

def send_otp_email(request, user, otp_code, expiry_minutes=1):
    
    user_name = (
        user.get_full_name()
        or getattr(user, 'full_name', None)
        or user.email.split('@')[0].capitalize()
    )

    context = {
        'user_name' : user_name,
        'otp'       : otp_code,
        'otp_digits': list(otp_code),
        'expiry_minutes': expiry_minutes,
        'logo_url': 'cid:glowe_logo',
    }

    html_content = render_to_string(
        'accounts/email/otp_email.html',
        context
    )

    email = EmailMultiAlternatives(
        subject  = 'Your Glowé Verification Code',
        body     = f'Hi {user_name},\n\nYour verification code is: {otp_code}\n\nThis code expires in {expiry_minutes} minute(s).\n\nThe Glowé Team',
        from_email = settings.EMAIL_HOST_USER,
        to         = [user.email],
    )
    email.attach_alternative(html_content, 'text/html')

    # Attach the logo physical file directly inside the email
    logo_path = os.path.join(settings.BASE_DIR, 'core', 'static', 'core', 'images', 'logo.png')
    try:
        with open(logo_path, 'rb') as img_file:
            logo_img = MIMEImage(img_file.read())
            logo_img.add_header('Content-ID', '<glowe_logo>')
            logo_img.add_header('Content-Disposition', 'inline', filename='logo.png')
            email.attach(logo_img)
    except Exception:
        pass # Fallback gracefully if logo file isn't found
        
    email.send(fail_silently=False)

def send_password_reset_email(request, user, reset_link, expiry_minutes=15):
    
    user_name = (
        user.get_full_name()
        or getattr(user, 'full_name', None)
        or user.email.split('@')[0].capitalize()
    )

    context = {
        'user_name' : user_name,
        'reset_link': reset_link,
        'expiry_minutes': expiry_minutes,
        'logo_url'  : 'cid:glowe_logo',
    }

    html_content = render_to_string(
        'accounts/email/reset_password_email.html',
        context
    )

    email = EmailMultiAlternatives(
        subject    = 'Reset Your Glowé Password',
        body       = f'Hi {user_name},\n\nPlease use the link below to reset your password:\n\n{reset_link}\n\nThis link expires in {expiry_minutes} minutes.\n\nThe Glowé Team',
        from_email = settings.EMAIL_HOST_USER,
        to         = [user.email],
    )
    email.attach_alternative(html_content, 'text/html')

    # Attach the logo physical file directly inside the email
    logo_path = os.path.join(settings.BASE_DIR, 'core', 'static', 'core', 'images', 'logo.png')
    try:
        with open(logo_path, 'rb') as img_file:
            logo_img = MIMEImage(img_file.read())
            logo_img.add_header('Content-ID', '<glowe_logo>')
            logo_img.add_header('Content-Disposition', 'inline', filename='logo.png')
            email.attach(logo_img)
    except Exception:
        pass
        
    email.send(fail_silently=False)

def send_admin_otp_email(user, otp_code, expiry_minutes=2):
    """
    Sends a premium luxury-tier Admin OTP email for password resets.
    """
    context = {
        'user_name' : 'Admin',
        'otp'       : otp_code,
        'otp_digits': list(otp_code),
        'expiry_minutes': expiry_minutes,
        'logo_url': 'cid:glowe_logo',
    }

    html_content = render_to_string(
        'adminpanel/email/admin_otp_email.html',
        context
    )

    email = EmailMultiAlternatives(
        subject      = 'Glowé Admin — OTP Verification Code',
        body         = f'Hello Admin,\n\nYour Admin Control Panel verification code is: {otp_code}\n\nThis code expires in {expiry_minutes} minutes.\n\nRegard,\nThe Glowé Team',
        from_email   = settings.EMAIL_HOST_USER,
        to           = [user.email],
    )
    email.attach_alternative(html_content, 'text/html')

    # Attach branding logo
    logo_path = os.path.join(settings.BASE_DIR, 'core', 'static', 'core', 'images', 'logo.png')
    try:
        with open(logo_path, 'rb') as img_file:
            logo_img = MIMEImage(img_file.read())
            logo_img.add_header('Content-ID', '<glowe_logo>')
            logo_img.add_header('Content-Disposition', 'inline', filename='logo.png')
            email.attach(logo_img)
    except Exception:
        pass
        
    email.send(fail_silently=False)
