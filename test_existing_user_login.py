#!/usr/bin/env python
"""
Test script to verify existing user login
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from users.models import UserProfile, Role

def test_existing_user_login():
    """Test login with existing users"""
    
    print("=== EXISTING USER LOGIN TEST ===")
    
    # Test with known users
    test_users = [
        {'email': 'chethan@gmail.com', 'password': 'password123'},  # Known user
        {'email': 'sath@gmail.com', 'password': 'password123'},     # Known admin
        {'email': 'siva@gmail.com', 'password': 'password123'},      # Known user
    ]
    
    for test_user in test_users:
        print(f"\nTesting login for: {test_user['email']}")
        
        try:
            # Find user by email
            user = User.objects.get(email=test_user['email'])
            print(f"  User found: {user.username}")
            print(f"  User active: {user.is_active}")
            
            # Check UserProfile
            user_profile = getattr(user, 'userprofile', None)
            if user_profile:
                print(f"  Role: {user_profile.role.name if user_profile.role else 'No Role'}")
                print(f"  Profile active: {user_profile.is_active}")
                
                # Test authentication
                authenticated_user = authenticate(username=test_user['email'], password=test_user['password'])
                if authenticated_user:
                    print(f"  Authentication: SUCCESS")
                    print(f"  Can login to user dashboard: {'Yes' if not _is_admin(authenticated_user) and not _is_agent(authenticated_user) else 'No (wrong role)'}")
                else:
                    print(f"  Authentication: FAILED (wrong password)")
            else:
                print(f"  UserProfile: NOT FOUND")
                
        except User.DoesNotExist:
            print(f"  User: NOT FOUND")
        except Exception as e:
            print(f"  Error: {e}")
    
    print("\n=== TEST COMPLETE ===")

def _is_admin(user):
    """Helper function to check if user is admin"""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if hasattr(user, "userprofile") and getattr(user.userprofile, "role", None):
        return (getattr(user.userprofile.role, "name", "").lower() in ["admin", "superadmin"])
    return False

def _is_agent(user):
    """Helper function to check if user is agent"""
    if not user or not user.is_authenticated:
        return False
    if hasattr(user, "userprofile") and getattr(user.userprofile, "role", None):
        return (getattr(user.userprofile.role, "name", "").lower() == "agent")
    return False

if __name__ == '__main__':
    test_existing_user_login()
