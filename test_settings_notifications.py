#!/usr/bin/env python
"""
Test script to verify notification settings on settings page
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from users.models import UserProfile

def test_notification_settings():
    """Test notification settings on settings page"""
    print("Testing notification settings functionality...")
    
    try:
        # Get current user
        user = User.objects.first()
        if not user:
            print("❌ No users found in database.")
            return
            
        print(f"👤 Testing with user: {user.username}")
        
        # Get or create user profile
        profile, created = UserProfile.objects.get_or_create(user=user)
        
        if created:
            print("📝 Created new user profile")
        
        # Create test client
        client = Client()
        
        # Login the user
        login_success = client.login(username=user.username, password='admin123')
        if not login_success:
            print("❌ Login failed. Please check user credentials.")
            return
        
        print(f"✅ User logged in successfully")
        
        # Test settings page access
        response = client.get('/dashboard/user-dashboard/settings/')
        
        if response.status_code == 200:
            print(f"✅ Settings page accessible (status: {response.status_code})")
        else:
            print(f"❌ Settings page not accessible (status: {response.status_code})")
            return
        
        # Check if notification settings are present in the template
        content = response.content.decode('utf-8')
        
        if 'Email Notifications' in content:
            print(f"✅ Email notifications setting found in template")
        else:
            print(f"❌ Email notifications setting not found in template")
        
        if 'Push Notifications' in content:
            print(f"✅ Push notifications setting found in template")
        else:
            print(f"❌ Push notifications setting not found in template")
        
        if 'Marketing Emails' in content:
            print(f"✅ Marketing emails setting found in template")
        else:
            print(f"❌ Marketing emails setting not found in template")
        
        # Test notification settings update
        print(f"\n🔄 Testing notification settings update...")
        
        # Enable all notifications
        profile.email_notifications = False
        profile.desktop_notifications = False
        profile.allow_dm_from_non_contacts = False
        profile.save()
        
        print(f"📧 Before: Email notifications = {profile.email_notifications}")
        print(f"📱 Before: Push notifications = {profile.desktop_notifications}")
        print(f"📢 Before: Marketing emails = {profile.allow_dm_from_non_contacts}")
        
        # Submit settings form with all notifications enabled
        settings_data = {
            'action': 'settings',
            'theme': 'light',
            'email_notifications': 'on',  # Checkbox sends 'on' when checked
            'push_notifications': 'on',
            'marketing_emails': 'on',
        }
        
        response = client.post('/dashboard/user-dashboard/settings/', settings_data)
        
        if response.status_code == 200:
            print(f"✅ Settings form submitted successfully")
        else:
            print(f"❌ Settings form submission failed (status: {response.status_code})")
        
        # Check if settings were updated
        profile.refresh_from_db()
        
        print(f"📧 After: Email notifications = {profile.email_notifications}")
        print(f"📱 After: Push notifications = {profile.desktop_notifications}")
        print(f"📢 After: Marketing emails = {profile.allow_dm_from_non_contacts}")
        
        if profile.email_notifications and profile.desktop_notifications and profile.allow_dm_from_non_contacts:
            print(f"✅ All notification settings updated successfully!")
        else:
            print(f"❌ Some notification settings were not updated")
        
        # Test disabling notifications
        print(f"\n🔕 Testing notification settings disable...")
        
        settings_data = {
            'action': 'settings',
            'theme': 'light',
            # No checkboxes = disabled
        }
        
        response = client.post('/dashboard/user-dashboard/settings/', settings_data)
        
        if response.status_code == 200:
            print(f"✅ Settings form submitted successfully")
        else:
            print(f"❌ Settings form submission failed (status: {response.status_code})")
        
        # Check if settings were updated
        profile.refresh_from_db()
        
        print(f"📧 After disable: Email notifications = {profile.email_notifications}")
        print(f"📱 After disable: Push notifications = {profile.desktop_notifications}")
        print(f"📢 After disable: Marketing emails = {profile.allow_dm_from_non_contacts}")
        
        if not profile.email_notifications and not profile.desktop_notifications and not profile.allow_dm_from_non_contacts:
            print(f"✅ All notification settings disabled successfully!")
        else:
            print(f"❌ Some notification settings were not disabled")
        
        print(f"\n🎉 Notification settings test completed!")
        
    except Exception as e:
        print(f"❌ Error testing notification settings: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_notification_settings()
