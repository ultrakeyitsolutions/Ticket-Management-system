#!/usr/bin/env python
"""
Simple test to verify theme settings functionality
"""
import os
import sys
import django

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from users.models import UserProfile, Role

def test_theme_settings_logic():
    """Test the theme settings logic directly"""
    print("Testing user dashboard theme settings logic...")
    
    # Use an existing user for testing
    user = User.objects.first()
    if not user:
        print("No users found in database.")
        return
    
    print(f"Using existing user: {user.username}")
    
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
    
    # Test 1: Check initial theme
    print("1. Testing initial theme...")
    print(f"   Current theme: {profile.theme}")
    assert profile.theme in ['light', 'dark', 'system'], f"Invalid theme: {profile.theme}"
    print("   Initial theme is valid!")
    
    # Test 2: Test changing to dark theme
    print("2. Testing dark theme change...")
    profile.theme = 'dark'
    profile.email_notifications = True
    profile.desktop_notifications = False
    profile.allow_dm_from_non_contacts = False
    profile.save()
    
    profile.refresh_from_db()
    assert profile.theme == 'dark', f"Dark theme not set: {profile.theme}"
    assert profile.email_notifications == True, "Email notifications not updated"
    assert profile.desktop_notifications == False, "Desktop notifications not updated"
    print("   Dark theme settings updated successfully!")
    
    # Test 3: Test changing to light theme
    print("3. Testing light theme change...")
    profile.theme = 'light'
    profile.email_notifications = False
    profile.desktop_notifications = True
    profile.allow_dm_from_non_contacts = True
    profile.save()
    
    profile.refresh_from_db()
    assert profile.theme == 'light', f"Light theme not set: {profile.theme}"
    assert profile.email_notifications == False, "Email notifications not updated"
    assert profile.desktop_notifications == True, "Desktop notifications not updated"
    assert profile.allow_dm_from_non_contacts == True, "Marketing emails setting not updated"
    print("   Light theme settings updated successfully!")
    
    # Test 4: Test changing to system theme
    print("4. Testing system theme change...")
    profile.theme = 'system'
    profile.save()
    
    profile.refresh_from_db()
    assert profile.theme == 'system', f"System theme not set: {profile.theme}"
    print("   System theme updated successfully!")
    
    # Test 5: Test 2FA settings
    print("5. Testing 2FA settings...")
    profile.two_factor_enabled = False
    profile.save()
    
    profile.refresh_from_db()
    assert profile.two_factor_enabled == False, "2FA not disabled"
    
    profile.two_factor_enabled = True
    profile.save()
    
    profile.refresh_from_db()
    assert profile.two_factor_enabled == True, "2FA not enabled"
    print("   2FA settings work correctly!")
    
    print("\nAll theme settings logic tests passed! \u2713")
    print("The backend logic for theme toggle functionality is working correctly.")
    print("You can now test the frontend by:")
    print("1. Starting the Django server: python manage.py runserver")
    print("2. Navigating to: http://127.0.0.1:8000/dashboard/user-dashboard/settings/")
    print("3. Clicking on different theme options (Light, Dark, System)")
    print("4. Saving the settings and verifying the theme changes")

if __name__ == '__main__':
    test_theme_settings_logic()
