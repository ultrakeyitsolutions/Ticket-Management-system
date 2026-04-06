#!/usr/bin/env python
"""
Test notification form submission
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.contrib.auth.models import User
from users.models import UserProfile
from django.test import RequestFactory
from django.contrib.messages.storage.fallback import FallbackStorage
from dashboards.views import _build_agent_profile_ctx

def test_notification_save():
    print("Testing Notification Form Submission...")
    
    # Get the test agent user
    user = User.objects.get(username='testagent')
    profile = UserProfile.objects.get(user=user)
    
    print(f"Initial state:")
    print(f"  email_notifications: {profile.email_notifications}")
    print(f"  desktop_notifications: {profile.desktop_notifications}")
    
    # Create request factory
    factory = RequestFactory()
    
    # Test 1: Enable both notifications
    print("\n1. Testing: Enable both notifications...")
    request = factory.post('/dashboard/agent-dashboard/profile.html', {
        'action': 'notifications',
        'email_notifications': 'on',
        'desktop_notifications': 'on',
        'show_activity_status': 'on',
        'allow_dm_from_non_contacts': 'on'
    })
    request.user = user
    request.session = {}
    request._messages = FallbackStorage(request)
    
    # Process the form
    ctx = _build_agent_profile_ctx(request)
    
    # Check results
    profile.refresh_from_db()
    print(f"After save:")
    print(f"  email_notifications: {profile.email_notifications}")
    print(f"  desktop_notifications: {profile.desktop_notifications}")
    print(f"  profile_saved: {ctx.get('profile_saved')}")
    
    # Test 2: Disable desktop notifications only
    print("\n2. Testing: Disable desktop notifications only...")
    request = factory.post('/dashboard/agent-dashboard/profile.html', {
        'action': 'notifications',
        'email_notifications': 'on',  # Keep enabled
        'show_activity_status': 'on',
        'allow_dm_from_non_contacts': 'on'
        # desktop_notifications not sent = should be False
    })
    request.user = user
    request.session = {}
    request._messages = FallbackStorage(request)
    
    # Process the form
    ctx = _build_agent_profile_ctx(request)
    
    # Check results
    profile.refresh_from_db()
    print(f"After save:")
    print(f"  email_notifications: {profile.email_notifications}")
    print(f"  desktop_notifications: {profile.desktop_notifications}")
    print(f"  profile_saved: {ctx.get('profile_saved')}")
    
    # Test 3: Test GET request to see context
    print("\n3. Testing GET request context...")
    request = factory.get('/dashboard/agent-dashboard/profile.html')
    request.user = user
    request.session = {}
    request._messages = FallbackStorage(request)
    
    ctx = _build_agent_profile_ctx(request)
    print(f"Context variables:")
    print(f"  notif_email: {ctx.get('notif_email')}")
    print(f"  notif_desktop: {ctx.get('notif_desktop')}")
    print(f"  profile_saved: {ctx.get('profile_saved')}")

if __name__ == '__main__':
    test_notification_save()
