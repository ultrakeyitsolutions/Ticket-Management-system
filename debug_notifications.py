#!/usr/bin/env python
"""
Debug notification form by rendering the template
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
from django.template.loader import render_to_string
from django.contrib.messages.storage.fallback import FallbackStorage
from dashboards.views import _build_agent_profile_ctx

def debug_notifications():
    print("Debugging Notification Form...")
    
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
    for key in ['notif_email', 'notif_desktop', 'notif_show_activity', 'notif_allow_dm']:
        print(f"  {key}: {ctx.get(key, 'MISSING')}")
    
    # Try to render just the notifications section
    try:
        # Create a minimal template to test the checkbox logic
        template_content = """
        Email: <input type="checkbox" name="email_notifications" {% if notif_email %}checked{% endif %}>
        Desktop: <input type="checkbox" name="desktop_notifications" {% if notif_desktop %}checked{% endif %}>
        """
        
        from django.template import Template, Context
        template = Template(template_content)
        rendered = template.render(Context(ctx))
        
        print(f"\nRendered HTML:")
        print(rendered)
        
    except Exception as e:
        print(f"Error rendering template: {e}")
    
    # Check if the profile_saved flag is being set correctly
    print(f"\nProfile saved flag: {ctx.get('profile_saved', 'MISSING')}")

if __name__ == '__main__':
    debug_notifications()
