#!/usr/bin/env python
"""
Debug settings save error
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
from dashboards.views import _build_agent_settings_ctx
from dashboards.models import SiteSettings

def debug_settings_error():
    print("Debugging Settings Save Error...")
    
    # Get the test agent user
    user = User.objects.get(username='testagent')
    print(f"Using test agent: {user.username}")
    
    # Create request factory
    factory = RequestFactory()
    
    # Test the exact data from console log
    print("\n1. Testing with exact console data...")
    request = factory.post('/dashboard/agent-dashboard/settings.html', {
        'csrfmiddlewaretoken': 'mVvELKt1QCe2h2x4YEGS4ccCUA6mgiPFOYgp0ewCYbt0d768vTqFFY3dyTrHVIec',
        'company_name': 'Ultrakey it solutions',
        'website_url': 'support@ultrakeyit.com',  # This might be the issue - URL field expects URL format
        'contact_email': 'support@ultrakeyit.com',
        'contact_phone': '',
        'address': '',
        'default_language': 'English (United States)',
        'time_zone': '(UTC+05:30) India',
        'date_format': 'DD/MM/YYYY',
        'time_format': '12-hour',
        'first_day_of_week': '1',
        'currency': 'USD - US Dollar ($)',
        'theme': 'light',
        'maintenance_mode': 'off',  # This might be the issue - checkboxes send 'on' or nothing
        'user_registration': 'off',
        'email_verification': 'off',
        'remember_me': 'off',
        'show_tutorial': 'off'
    })
    request.user = user
    request.session = {}
    request._messages = FallbackStorage(request)
    request.META['HTTP_X_REQUESTED_WITH'] = 'XMLHttpRequest'
    
    try:
        response = _build_agent_settings_ctx(request)
        print(f"Response: {response}")
        print(f"Response type: {type(response)}")
        
        if hasattr(response, 'content'):
            print(f"Response content: {response.content.decode()}")
    except Exception as e:
        print(f"Exception occurred: {e}")
        import traceback
        traceback.print_exc()
    
    # Test with corrected data
    print("\n2. Testing with corrected data...")
    request = factory.post('/dashboard/agent-dashboard/settings.html', {
        'csrfmiddlewaretoken': 'mVvELKt1QCe2h2x4YEGS4ccCUA6mgiPFOYgp0ewCYbt0d768vTqFFY3dyTrHVIec',
        'company_name': 'Ultrakey it solutions',
        'website_url': 'https://ultrakeyit.com',  # Corrected URL format
        'contact_email': 'support@ultrakeyit.com',
        'contact_phone': '',
        'address': '',
        'default_language': 'English (United States)',
        'time_zone': '(UTC+05:30) India',
        'date_format': 'DD/MM/YYYY',
        'time_format': '12-hour',
        'first_day_of_week': '1',
        'currency': 'USD - US Dollar ($)',
        'theme': 'light',
        # Note: unchecked checkboxes don't send any value, so we don't include them
    })
    request.user = user
    request.session = {}
    request._messages = FallbackStorage(request)
    request.META['HTTP_X_REQUESTED_WITH'] = 'XMLHttpRequest'
    
    try:
        response = _build_agent_settings_ctx(request)
        print(f"Response: {response}")
        
        if hasattr(response, 'content'):
            print(f"Response content: {response.content.decode()}")
    except Exception as e:
        print(f"Exception occurred: {e}")
        import traceback
        traceback.print_exc()
    
    # Check current settings
    print("\n3. Checking current settings...")
    settings_obj = SiteSettings.get_solo()
    print(f"Current settings:")
    print(f"  company_name: '{settings_obj.company_name}'")
    print(f"  website_url: '{settings_obj.website_url}'")
    print(f"  contact_email: '{settings_obj.contact_email}'")

if __name__ == '__main__':
    debug_settings_error()
