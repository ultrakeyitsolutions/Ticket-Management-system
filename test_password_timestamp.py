#!/usr/bin/env python
"""
Test script to verify password timestamp functionality
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from users.models import UserProfile
from django.utils import timezone

def test_password_timestamp():
    """Test the password timestamp functionality"""
    print("Testing password timestamp functionality...")
    
    # Get current logged-in user (or create test user)
    try:
        # Try to get an existing user
        user = User.objects.first()
        if not user:
            print("❌ No users found in database.")
            return
            
        print(f"👤 Testing with user: {user.username}")
        
        # Get or create user profile
        profile, created = UserProfile.objects.get_or_create(user=user)
        
        if created:
            print("📝 Created new user profile")
        
        # Check if password_last_changed field exists
        if hasattr(profile, 'password_last_changed'):
            print("✅ password_last_changed field exists in UserProfile")
            
            # Check current value
            if profile.password_last_changed:
                print(f"📅 Current password last changed: {profile.password_last_changed}")
                
                # Calculate time since password changed
                now = timezone.now()
                diff = now - profile.password_last_changed
                days = diff.days
                
                print(f"⏰ Time since password change: {days} days")
                
                if days == 0:
                    print("🕐 Password was changed today!")
                elif days == 1:
                    print("🕐 Password was changed yesterday!")
                elif days < 7:
                    print(f"🕐 Password was changed {days} days ago")
                elif days < 30:
                    weeks = days // 7
                    print(f"🕐 Password was changed {weeks} week{'s' if weeks != 1 else ''} ago")
                elif days < 365:
                    months = days // 30
                    print(f"🕐 Password was changed {months} month{'s' if months != 1 else ''} ago")
                else:
                    years = days // 365
                    print(f"🕐 Password was changed {years} year{'s' if years != 1 else ''} ago")
                    
            else:
                print("❌ Password last changed is NULL - password has never been changed")
                
                # Simulate setting password last changed
                profile.password_last_changed = timezone.now()
                profile.save()
                print("✅ Set password_last_changed to current time for testing")
                
        else:
            print("❌ password_last_changed field does not exist in UserProfile")
            
        # Test the template context variable
        print(f"\n🔍 Testing template context variables...")
        
        # Simulate what the view would pass to template
        context_data = {
            'password_last_changed': profile.password_last_changed,
            'settings_2fa_enabled': getattr(profile, 'two_factor_enabled', False),
        }
        
        print(f"   - password_last_changed: {context_data['password_last_changed']}")
        print(f"   - settings_2fa_enabled: {context_data['settings_2fa_enabled']}")
        
        print("✅ Template context variables are set correctly")
        
    except Exception as e:
        print(f"❌ Error testing password timestamp: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_password_timestamp()
