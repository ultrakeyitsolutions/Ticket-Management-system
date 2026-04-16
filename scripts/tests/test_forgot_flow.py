#!/usr/bin/env python
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import RequestFactory, Client
from django.contrib.sessions.backends.db import SessionStore
from superadmin.views import superadmin_forgot_password, superadmin_reset_password
from django.contrib.auth.models import User
from superadmin.views import _is_superadmin_user

print("=== Testing Forgot Password Flow ===")
print()

# Create a test request
factory = RequestFactory()
client = Client()

# Test with a valid superadmin email
test_email = "arikatlasathvika98@gmail.com"
print(f"Testing with email: {test_email}")

# Check if user exists and is superadmin
user = User.objects.filter(email=test_email).first()
if user and _is_superadmin_user(user):
    print("User found and is superadmin")
    
    # Test forgot password request
    request = factory.post('/superadmin/forgot-password/', {'email': test_email})
    request.session = SessionStore()
    
    print("Sending forgot password request...")
    response = superadmin_forgot_password(request)
    
    print(f"Response status: {response.status_code}")
    print(f"Response type: {type(response)}")
    
    # Check session for verification code
    session_key = f'reset_code_{test_email}'
    if session_key in request.session:
        session_data = request.session[session_key]
        print(f"Verification code stored: {session_data['code']}")
        print(f"Timestamp: {session_data['timestamp']}")
        print("SUCCESS: Verification code generated and stored")
    else:
        print("ERROR: No verification code found in session")
        
    # Check messages
    from django.contrib.messages import get_messages
    messages = list(get_messages(request))
    if messages:
        for message in messages:
            print(f"Message: {message.message} (level: {message.level})")
    
else:
    print("User not found or not superadmin")

print("\n=== Testing Reset Password Page ===")

# Test reset password page access
request = factory.get('/superadmin/reset-password/')
request.session = SessionStore()

# Add test session data
import time
from django.utils import timezone
request.session[f'reset_code_{test_email}'] = {
    'code': '123456',
    'timestamp': str(timezone.now().timestamp()),
    'email': test_email
}
request.session.modified = True

response = superadmin_reset_password(request)
print(f"Reset password page status: {response.status_code}")

print("\n=== Instructions for Manual Testing ===")
print("1. Go to: http://127.0.0.1:8000/superadmin/forgot-password/")
print(f"2. Enter email: {test_email}")
print("3. Check the server console for debug output")
print("4. Check your email for verification code")
print("5. Go to reset page and enter the code")
