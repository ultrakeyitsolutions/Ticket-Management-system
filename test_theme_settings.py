#!/usr/bin/env python
"""
Test script to verify user dashboard theme settings functionality
"""
import os
import sys
import django

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import TestCase, Client
from django.contrib.auth.models import User
from users.models import UserProfile, Role

def test_theme_settings():
    """Test the theme settings functionality"""
    print("Testing user dashboard theme settings...")
    
    # Use an existing user for testing
    user = User.objects.first()
    if not user:
        print("No users found in database. Please create a user first.")
        return
    
    # Get or create user profile
    profile, created = UserProfile.objects.get_or_create(
        user=user,
        defaults={
            'theme': 'system',
            'email_notifications': True,
            'desktop_notifications': False,
            'allow_dm_from_non_contacts': False
        }
    )
    
    if created:
        print(f"Created new profile for user: {user.username}")
    else:
        print(f"Using existing profile for user: {user.username}")
    
    client = Client()
    
    # For testing, we'll create a simple test session instead of requiring password
    from django.contrib.sessions.backends.db import SessionStore
    session = SessionStore()
    session['user_id'] = user.id
    session.save()
    
    client.cookies[session.session_key] = session.session_key
    
    # Test 1: Check if settings page loads
    print("1. Testing settings page load...")
    response = client.get('/dashboard/user-dashboard/settings/')
    assert response.status_code == 200, f"Settings page failed to load: {response.status_code}"
    print("   Settings page loads successfully!")
    
    # Test 2: Test theme form submission
    print("2. Testing theme form submission...")
    response = client.post('/dashboard/user-dashboard/settings/', {
        'action': 'settings',
        'theme': 'dark',
        'email_notifications': 'on',
        'push_notifications': 'off',
        'marketing_emails': 'off'
    })
    
    # Check if profile was updated
    profile.refresh_from_db()
    assert profile.theme == 'dark', f"Theme not updated: {profile.theme}"
    assert profile.email_notifications == True, "Email notifications not updated"
    assert profile.desktop_notifications == False, "Desktop notifications not updated"
    print("   Theme settings updated successfully!")
    
    # Test 3: Test switching to light theme
    print("3. Testing light theme switch...")
    response = client.post('/dashboard/user-dashboard/settings/', {
        'action': 'settings',
        'theme': 'light',
        'email_notifications': 'off',
        'push_notifications': 'on',
        'marketing_emails': 'on'
    })
    
    profile.refresh_from_db()
    assert profile.theme == 'light', f"Light theme not set: {profile.theme}"
    assert profile.email_notifications == False, "Email notifications not updated"
    assert profile.desktop_notifications == True, "Desktop notifications not updated"
    assert profile.allow_dm_from_non_contacts == True, "Marketing emails setting not updated"
    print("   Light theme settings updated successfully!")
    
    # Test 4: Test system theme
    print("4. Testing system theme...")
    response = client.post('/dashboard/user-dashboard/settings/', {
        'action': 'settings',
        'theme': 'system'
    })
    
    profile.refresh_from_db()
    assert profile.theme == 'system', f"System theme not set: {profile.theme}"
    print("   System theme updated successfully!")
    
    print("\nAll theme settings tests passed! \u2713")
    print("The theme toggle functionality should now work correctly in the user dashboard.")

if __name__ == '__main__':
    test_theme_settings()
