#!/usr/bin/env python
"""
Test script to check if pandu can access dashboard directly
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.test import RequestFactory, Client
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.messages.middleware import MessageMiddleware

def test_dashboard_access():
    """Test if pandu can access dashboard"""
    print("Testing dashboard access for pandu user...")
    
    try:
        # Get the pandu user
        user = User.objects.get(username='pandu')
        print(f"✅ User found: {user.username}")
        
        # Create a test client
        client = Client()
        
        # Test direct login with client
        print(f"\n🔐 Testing login with Django test client...")
        
        # Try to login (you'll need to provide password)
        test_password = input("Enter pandu's password for client test (or press Enter to skip): ").strip()
        
        if test_password:
            # Test login
            login_success = client.login(username='pandu', password=test_password)
            
            if login_success:
                print(f"✅ Client login successful!")
                
                # Test accessing dashboard
                print(f"\n🏠 Testing dashboard access...")
                
                response = client.get('/dashboard/user-dashboard/')
                
                print(f"   - Response status: {response.status_code}")
                print(f"   - Response content type: {response.get('Content-Type', 'Not set')}")
                
                if response.status_code == 200:
                    print(f"✅ Dashboard access successful!")
                    print(f"   - Page content length: {len(response.content)} bytes")
                    
                    # Check if it contains expected content
                    if b'My Tickets' in response.content:
                        print(f"✅ Dashboard content looks correct!")
                    else:
                        print(f"⚠️  Dashboard content might be wrong")
                        
                elif response.status_code == 302:
                    print(f"🔄 Redirected to: {response.get('Location', 'Unknown')}")
                    
                elif response.status_code == 403:
                    print(f"❌ FORBIDDEN - Access denied!")
                    print(f"   - This suggests a permission or middleware issue")
                    
                else:
                    print(f"❌ Unexpected status code: {response.status_code}")
                    
                # Check response content for error messages
                if b'forbidden' in response.content.lower():
                    print(f"❌ 'forbidden' found in response content")
                if b'error' in response.content.lower():
                    print(f"❌ 'error' found in response content")
                    
            else:
                print(f"❌ Client login failed!")
        else:
            print("⚠️  Skipping client test")
            
        # Test accessing settings page specifically
        print(f"\n⚙️  Testing settings page access...")
        
        if test_password:
            if client.login(username='pandu', password=test_password):
                response = client.get('/dashboard/user-dashboard/settings/')
                
                print(f"   - Settings page status: {response.status_code}")
                
                if response.status_code == 200:
                    print(f"✅ Settings page accessible!")
                    
                    # Check if password last changed is in the content
                    if b'password_last_changed' in response.content or b'Last changed' in response.content:
                        print(f"✅ Settings page contains password timestamp!")
                    else:
                        print(f"⚠️  Settings page might not have password timestamp")
                        
                elif response.status_code == 403:
                    print(f"❌ Settings page FORBIDDEN!")
                else:
                    print(f"❌ Settings page unexpected status: {response.status_code}")
                    
    except User.DoesNotExist:
        print(f"❌ User 'pandu' not found")
    except Exception as e:
        print(f"❌ Error testing dashboard access: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_dashboard_access()
