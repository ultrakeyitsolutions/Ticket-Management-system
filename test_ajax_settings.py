#!/usr/bin/env python
"""
Test AJAX settings request exactly like JavaScript
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.contrib.auth.models import User
from django.test import RequestFactory, Client
from django.contrib.messages.storage.fallback import FallbackStorage
from dashboards.views import agent_dashboard_page
from dashboards.models import SiteSettings

def test_ajax_settings():
    print("Testing AJAX Settings Request...")
    
    # Use Django test client for more realistic testing
    client = Client()
    
    # Get the test agent user and login
    user = User.objects.get(username='testagent')
    client.force_login(user)
    
    # Test 1: Test with exact data from console
    print("\n1. Testing AJAX POST with console data...")
    response = client.post(
        '/dashboard/agent-dashboard/settings.html',
        data={
            'csrfmiddlewaretoken': 'test-token',
            'company_name': 'Ultrakey it solutions',
            'website_url': 'support@ultrakeyit.com',  # Invalid URL format
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
            'maintenance_mode': 'off',
            'user_registration': 'off',
            'email_verification': 'off',
            'remember_me': 'off',
            'show_tutorial': 'off'
        },
        HTTP_X_REQUESTED_WITH='XMLHttpRequest'
    )
    
    print(f"Response status code: {response.status_code}")
    print(f"Response content: {response.content.decode()}")
    print(f"Response headers: {dict(response.headers)}")
    
    # Test 2: Test with corrected data
    print("\n2. Testing AJAX POST with corrected data...")
    response = client.post(
        '/dashboard/agent-dashboard/settings.html',
        data={
            'csrfmiddlewaretoken': 'test-token',
            'company_name': 'Ultrakey it solutions',
            'website_url': 'https://ultrakeyit.com',  # Valid URL format
            'contact_email': 'support@ultrakeyit.com',
            'contact_phone': '',
            'address': '',
            'default_language': 'English (United States)',
            'time_zone': '(UTC+05:30) India',
            'date_format': 'DD/MM/YYYY',
            'time_format': '12-hour',
            'first_day_of_week': '1',
            'currency': 'USD - US Dollar ($)',
            'theme': 'light'
            # Note: unchecked checkboxes are not included
        },
        HTTP_X_REQUESTED_WITH='XMLHttpRequest'
    )
    
    print(f"Response status code: {response.status_code}")
    print(f"Response content: {response.content.decode()}")
    
    # Test 3: Test regular POST (non-AJAX)
    print("\n3. Testing regular POST (non-AJAX)...")
    response = client.post(
        '/dashboard/agent-dashboard/settings.html',
        data={
            'csrfmiddlewaretoken': 'test-token',
            'company_name': 'Regular Test Company',
            'website_url': 'https://test.com',
            'contact_email': 'test@test.com',
        }
    )
    
    print(f"Response status code: {response.status_code}")
    print(f"Is redirect: {response.status_code in [302, 303]}")
    
    # Test 4: Check current settings
    print("\n4. Checking current settings...")
    settings_obj = SiteSettings.get_solo()
    print(f"Current settings:")
    print(f"  company_name: '{settings_obj.company_name}'")
    print(f"  website_url: '{settings_obj.website_url}'")
    print(f"  contact_email: '{settings_obj.contact_email}'")

if __name__ == '__main__':
    test_ajax_settings()
