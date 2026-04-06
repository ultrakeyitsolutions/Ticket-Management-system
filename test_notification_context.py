#!/usr/bin/env python
"""
Test notification context variables
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.contrib.auth.models import User
from django.test import RequestFactory
from django.contrib.messages.storage.fallback import FallbackStorage
from dashboards.views import _build_agent_profile_ctx

def test_notification_context():
    print("Testing Notification Context Variables...")
    
    # Get the test agent user
    user = User.objects.get(username='testagent')
    print(f"Using test agent: {user.username}")
    
    # Create request factory
    factory = RequestFactory()
    request = factory.get('/dashboard/agent-dashboard/profile.html')
    request.user = user
    request.session = {}
    request._messages = FallbackStorage(request)
    
    # Get context
    ctx = _build_agent_profile_ctx(request)
    
    print("\nContext Variables:")
    print(f"  notif_email: {ctx.get('notif_email', 'MISSING')}")
    print(f"  notif_desktop: {ctx.get('notif_desktop', 'MISSING')}")
    print(f"  notif_show_activity: {ctx.get('notif_show_activity', 'MISSING')}")
    print(f"  notif_allow_dm: {ctx.get('notif_allow_dm', 'MISSING')}")
    print(f"  profile_saved: {ctx.get('profile_saved', 'MISSING')}")
    
    print("\nTemplate Logic Simulation:")
    print(f"  Email checkbox checked: {'checked' if ctx.get('notif_email') else ''}")
    print(f"  Desktop checkbox checked: {'checked' if ctx.get('notif_desktop') else ''}")
    print(f"  Activity checkbox checked: {'checked' if ctx.get('notif_show_activity') else ''}")
    print(f"  DM checkbox checked: {'checked' if ctx.get('notif_allow_dm') else ''}")

if __name__ == '__main__':
    test_notification_context()
