#!/usr/bin/env python
"""
Test script to debug pandu user login issue
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from users.models import UserProfile
from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.messages.middleware import MessageMiddleware

def test_pandu_login():
    """Test pandu user login process"""
    print("Testing pandu user login...")
    
    try:
        # Get the pandu user
        user = User.objects.get(username='pandu')
        print(f"✅ User found: {user.username}")
        print(f"   - Email: {user.email}")
        print(f"   - Is active: {user.is_active}")
        print(f"   - Is staff: {user.is_staff}")
        print(f"   - Is superuser: {user.is_superuser}")
        
        # Check user profile
        try:
            profile = user.userprofile
            print(f"✅ Profile found:")
            print(f"   - Role: {profile.role}")
            print(f"   - Profile active: {profile.is_active}")
            print(f"   - Theme: {profile.theme}")
        except UserProfile.DoesNotExist:
            print("❌ No profile found for user")
            return
        except Exception as e:
            print(f"❌ Error accessing profile: {e}")
            return
        
        # Test authentication
        print(f"\n🔐 Testing authentication...")
        
        # Create a request factory
        factory = RequestFactory()
        
        # Test with correct password (you'll need to provide this)
        test_password = input("Enter pandu's password for testing (or press Enter to skip): ").strip()
        
        if test_password:
            # Create a mock request
            request = factory.post('/login/', {
                'username': 'pandu',
                'password': test_password
            })
            
            # Add session and message middleware
            session_middleware = SessionMiddleware(lambda req: None)
            session_middleware(request)
            
            message_middleware = MessageMiddleware(lambda req: None)
            message_middleware(request)
            
            # Test authentication
            authenticated_user = authenticate(request, username='pandu', password=test_password)
            
            if authenticated_user:
                print(f"✅ Authentication successful!")
                print(f"   - Authenticated user: {authenticated_user.username}")
                print(f"   - Is same user: {authenticated_user.id == user.id}")
                
                # Test login
                try:
                    login(request, authenticated_user)
                    print(f"✅ Login successful!")
                    print(f"   - Session key: {request.session.session_key}")
                except Exception as e:
                    print(f"❌ Login failed: {e}")
                    
            else:
                print(f"❌ Authentication failed!")
                print(f"   - Check password: {test_password != ''}")
                
        else:
            print("⚠️  Skipping password test")
            
        # Check role-based functions
        print(f"\n👥 Testing role functions...")
        
        # Test _is_admin function
        def _is_admin(user):
            if not user or not user.is_authenticated:
                return False
            if user.is_superuser:
                return True
            if hasattr(user, "userprofile") and getattr(user.userprofile, "role", None):
                return (getattr(user.userprofile.role, "name", "").lower() in ["admin", "superadmin"])
            return False
            
        def _is_agent(user):
            if not user or not user.is_authenticated:
                return False
            if hasattr(user, "userprofile") and getattr(user.userprofile, "role", None):
                return (getattr(user.userprofile.role, "name", "").lower() == "agent")
            return False
        
        print(f"   - Is admin: {_is_admin(user)}")
        print(f"   - Is agent: {_is_agent(user)}")
        
        # Test middleware behavior
        print(f"\n🔧 Testing middleware behavior...")
        
        # Simulate middleware check
        critical_users = [
            'pandu', 'testlogin', 'testuser', 'midhun', 
            'monika', 'sai1', 'customer1', 'customer2', 
            'customer3', 'ramesh', 'vasu', 'yash'
        ]
        
        if user.username in critical_users:
            print(f"✅ User {user.username} is in critical users list")
            print(f"   - Should be protected from deactivation")
        else:
            print(f"⚠️  User {user.username} is NOT in critical users list")
            
    except User.DoesNotExist:
        print(f"❌ User 'pandu' not found in database")
    except Exception as e:
        print(f"❌ Error testing pandu login: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_pandu_login()
