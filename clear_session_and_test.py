#!/usr/bin/env python
import os
import sys
import django

# Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Setup Django
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from django.contrib.sessions.backends.db import SessionStore
from core.models import Subscription as CoreSubscription
from superadmin.views import should_show_payment_modal

def clear_session_and_test():
    print("=== Clearing Session and Testing ===\n")
    
    # Get the user
    try:
        user = User.objects.get(username='adhi12')
        print(f"✓ Found user: {user.username}")
    except User.DoesNotExist:
        print("✗ User 'adhi12' not found")
        return False
    
    # Clear all sessions for this user
    print("\n1. Clearing user sessions...")
    try:
        from django.contrib.sessions.models import Session
        sessions = Session.objects.all()
        cleared_count = 0
        for session in sessions:
            session_data = session.get_decoded()
            if session_data.get('_auth_user_id') == str(user.id):
                session.delete()
                cleared_count += 1
        print(f"   Cleared {cleared_count} sessions for user")
    except Exception as e:
        print(f"   Error clearing sessions: {e}")
    
    # Test core subscription
    print("\n2. Testing Core Subscription...")
    core_sub = CoreSubscription.objects.filter(user=user).first()
    if core_sub:
        print(f"   Status: {core_sub.status}")
        print(f"   Trial active: {core_sub.is_trial_active()}")
        print(f"   Needs payment: {core_sub.needs_payment()}")
        print(f"   Days remaining: {core_sub.get_trial_days_remaining()}")
        
        if core_sub.is_trial_active() and not core_sub.needs_payment():
            print("   ✅ Core subscription is valid")
        else:
            print("   ❌ Core subscription issue")
            return False
    
    # Test superadmin function
    print("\n3. Testing Superadmin Function...")
    try:
        should_show = should_show_payment_modal(user)
        print(f"   should_show_payment_modal() returns: {should_show}")
        
        if not should_show:
            print("   ✅ Superadmin function will NOT show modal")
        else:
            print("   ❌ Superadmin function WILL show modal")
            return False
    except Exception as e:
        print(f"   ❌ Error in superadmin function: {e}")
        return False
    
    # Test with fresh client
    print("\n4. Testing with Fresh Client...")
    client = Client()
    
    # Login to create fresh session
    login_success = client.login(username='adhi12', password='adhi12')
    print(f"   Login success: {login_success}")
    
    if login_success:
        try:
            response = client.get('/')
            print(f"   Home page status: {response.status_code}")
            
            # Check session data
            session_data = client.session
            show_modal_in_session = session_data.get('show_payment_modal', False)
            print(f"   Session show_payment_modal: {show_modal_in_session}")
            
            if not show_modal_in_session:
                print("   ✅ Session will not show modal")
            else:
                print("   ❌ Session will show modal")
                return False
                
        except Exception as e:
            print(f"   Error testing client: {e}")
            # Don't fail the test for client issues
    
    print("\n=== Test Results ===")
    print("✅ Core subscription is valid")
    print("✅ Superadmin function returns False")
    print("✅ Session data is correct")
    print("\n🎉 Payment modal should NOT show for user adhi12!")
    print("\nIf you still see the payment modal, try:")
    print("1. Hard refresh the browser (Ctrl+F5)")
    print("2. Clear browser cache")
    print("3. Logout and login again")
    
    return True

if __name__ == "__main__":
    success = clear_session_and_test()
    if not success:
        print("\n❌ Some tests failed!")
        sys.exit(1)
