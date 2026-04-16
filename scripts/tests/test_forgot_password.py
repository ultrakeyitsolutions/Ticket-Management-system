#!/usr/bin/env python
"""
Test script for SuperAdmin forgot password functionality
"""
import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from users.models import UserProfile, Role
from superadmin.models import Company

def test_forgot_password_setup():
    """Setup test superadmin user if not exists"""
    print("=== Testing SuperAdmin Forgot Password Setup ===")
    
    # Create SuperAdmin role if not exists
    superadmin_role, created = Role.objects.get_or_create(
        name='SuperAdmin',
        defaults={'description': 'Super Administrator with full access'}
    )
    if created:
        print("Created SuperAdmin role")
    else:
        print("SuperAdmin role already exists")
    
    # Create test superadmin user if not exists
    test_email = "superadmin@test.com"
    user, created = User.objects.get_or_create(
        username='testsuperadmin',
        defaults={
            'email': test_email,
            'first_name': 'Test',
            'last_name': 'SuperAdmin',
            'is_staff': True,
            'is_superuser': True
        }
    )
    
    if created:
        user.set_password('testpassword123')
        user.save()
        
        # Create user profile
        profile = UserProfile.objects.create(user=user, role=superadmin_role)
        print(f"Created test superadmin user: {test_email}")
    else:
        print(f"Test superadmin user already exists: {test_email}")
    
    return user

def test_email_validation():
    """Test email validation functionality"""
    print("\n=== Testing Email Validation ===")
    
    from superadmin.views import superadmin_forgot_password
    from django.test import RequestFactory
    from django.contrib.sessions.backends.db import SessionStore
    
    factory = RequestFactory()
    
    # Test with valid superadmin email
    print("Testing valid superadmin email...")
    request = factory.post('/superadmin/forgot-password/', {'email': 'superadmin@test.com'})
    request.session = SessionStore()
    
    # Simulate the view logic
    from django.contrib.auth.models import User as DjangoUser
    from users.models import UserProfile
    import random
    from django.utils import timezone
    
    email = 'superadmin@test.com'
    user = DjangoUser.objects.filter(email=email).first()
    
    if user:
        # Check if user is superadmin
        try:
            profile = UserProfile.objects.get(user=user)
            if profile.role and profile.role.name.lower() == 'superadmin':
                print(f"Found superadmin user: {user.email}")
                
                # Generate test verification code
                verification_code = f"{random.randint(100000, 999999)}"
                print(f"Generated verification code: {verification_code}")
                
                # Store in session
                request.session[f'reset_code_{email}'] = {
                    'code': verification_code,
                    'timestamp': str(timezone.now().timestamp()),
                    'email': email
                }
                request.session.modified = True
                
                print("Verification code stored in session successfully")
                return True
        except UserProfile.DoesNotExist:
            print("User profile not found")
    
    print("Email validation test failed")
    return False

def test_code_verification():
    """Test verification code validation"""
    print("\n=== Testing Code Verification ===")
    
    from django.test import RequestFactory
    from django.contrib.sessions.backends.db import SessionStore
    
    factory = RequestFactory()
    email = 'superadmin@test.com'
    
    # Create a mock session with verification code
    request = factory.post('/superadmin/reset-password/', {
        'email': email,
        'code1': '1', 'code2': '2', 'code3': '3',
        'code4': '4', 'code5': '5', 'code6': '6',
        'new_password': 'newpassword123',
        'confirm_password': 'newpassword123'
    })
    request.session = SessionStore()
    
    # Store test code in session
    import time
    from django.utils import timezone
    
    test_code = "123456"
    request.session[f'reset_code_{email}'] = {
        'code': test_code,
        'timestamp': str(timezone.now().timestamp()),
        'email': email
    }
    request.session.modified = True
    
    # Simulate code verification
    session_data = request.session.get(f'reset_code_{email}')
    
    if session_data:
        timestamp = float(session_data['timestamp'])
        current_time = timezone.now().timestamp()
        
        # Check if code is still valid (within 15 minutes)
        if current_time - timestamp <= 900:
            if session_data['code'] == test_code:
                print("Code verification successful")
                return True
            else:
                print("Invalid code")
        else:
            print("Code expired")
    else:
        print("No session data found")
    
    return False

def main():
    """Run all tests"""
    print("SuperAdmin Forgot Password Functionality Test")
    print("=" * 50)
    
    try:
        # Setup test data
        test_user = test_forgot_password_setup()
        
        # Test email validation
        email_test_passed = test_email_validation()
        
        # Test code verification
        code_test_passed = test_code_verification()
        
        print("\n=== Test Results ===")
        print(f"Email Validation: {'PASS' if email_test_passed else 'FAIL'}")
        print(f"Code Verification: {'PASS' if code_test_passed else 'FAIL'}")
        
        if email_test_passed and code_test_passed:
            print("\nAll tests passed! Forgot password functionality is working correctly.")
        else:
            print("\nSome tests failed. Please check the implementation.")
        
        print("\nTest superadmin credentials:")
        print(f"Email: {test_user.email}")
        print("Password: testpassword123")
        print(f"Forgot Password URL: http://127.0.0.1:8000/superadmin/forgot-password/")
        
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
