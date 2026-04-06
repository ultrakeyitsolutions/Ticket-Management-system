#!/usr/bin/env python
"""
Test script to simulate browser behavior for agent password change
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

def test_browser_simulation():
    """Test agent password change with browser simulation"""
    print("Testing agent password change with browser simulation...")
    
    try:
        # Get agent user
        agent_user = User.objects.filter(username='testagent').first()
        if not agent_user:
            print("❌ Agent user not found")
            return
        
        print(f"👤 Testing with agent: {agent_user.username}")
        
        # Create test client
        client = Client()
        
        # Step 1: Login as agent
        print(f"\n🔐 Step 1: Login as agent")
        login_success = client.login(username='testagent', password='agent123')
        if not login_success:
            print("❌ Agent login failed")
            return
        
        print(f"✅ Agent logged in successfully")
        
        # Step 2: Access agent profile page
        print(f"\n📄 Step 2: Access agent profile page")
        response = client.get('/dashboard/agent-dashboard/profile/')
        
        if response.status_code == 200:
            print(f"✅ Profile page accessible")
        else:
            print(f"❌ Profile page not accessible: {response.status_code}")
            return
        
        # Step 3: Check if user is still authenticated
        print(f"\n🔍 Step 3: Check authentication status")
        response = client.get('/dashboard/agent-dashboard/')
        
        if response.status_code == 200:
            print(f"✅ User still authenticated after profile access")
        else:
            print(f"❌ User lost authentication: {response.status_code}")
            return
        
        # Step 4: Submit password change form
        print(f"\n🔄 Step 4: Submit password change form")
        password_data = {
            'action': 'password',
            'password': 'newagent456',
            'confirm': 'newagent456'
        }
        
        response = client.post('/dashboard/agent-dashboard/profile/', password_data, follow=True)
        
        print(f"📊 Response status: {response.status_code}")
        print(f"📊 Redirect chain: {response.redirect_chain}")
        
        # Check if redirected to login page
        final_url = response.request['PATH_INFO']
        if '/login' in final_url or final_url == '/':
            print(f"❌ User was redirected to login/landing page")
            print(f"❌ Final URL: {final_url}")
        else:
            print(f"✅ User stayed on dashboard")
            print(f"✅ Final URL: {final_url}")
        
        # Step 5: Check if user is still authenticated
        print(f"\n🔍 Step 5: Check authentication after password change")
        response = client.get('/dashboard/agent-dashboard/')
        
        if response.status_code == 200:
            print(f"✅ User still authenticated after password change")
        else:
            print(f"❌ User lost authentication after password change: {response.status_code}")
        
        # Step 6: Test new password works
        print(f"\n🔐 Step 6: Test new password")
        
        # Create new client to test new password
        new_client = Client()
        new_login = new_client.login(username='testagent', password='newagent456')
        
        if new_login:
            print(f"✅ New password works correctly")
        else:
            print(f"❌ New password doesn't work")
        
        # Step 7: Test old password doesn't work
        print(f"\n🔐 Step 7: Test old password")
        
        old_client = Client()
        old_login = old_client.login(username='testagent', password='agent123')
        
        if not old_login:
            print(f"✅ Old password correctly rejected")
        else:
            print(f"❌ Old password still works (security issue)")
        
        # Step 8: Check session data
        print(f"\n📊 Step 8: Check session data")
        
        # Get session from the original client
        session_data = dict(client.session)
        print(f"📊 Session keys: {list(session_data.keys())}")
        
        if 'tab_user_id' in session_data:
            print(f"✅ Tab user ID found: {session_data['tab_user_id']}")
        else:
            print(f"❌ Tab user ID not found")
        
        if 'tab_user_role' in session_data:
            print(f"✅ Tab user role found: {session_data['tab_user_role']}")
        else:
            print(f"❌ Tab user role not found")
        
        if '_auth_user_id' in session_data:
            print(f"✅ Auth user ID found: {session_data['_auth_user_id']}")
        else:
            print(f"❌ Auth user ID not found")
        
        if '_auth_user_hash' in session_data:
            print(f"✅ Auth user hash found")
        else:
            print(f"❌ Auth user hash not found")
        
        print(f"\n🎉 Browser simulation test completed!")
        
        # Reset password for future tests
        agent_user.set_password('agent123')
        agent_user.save()
        print(f"🔄 Reset password to agent123")
        
    except Exception as e:
        print(f"❌ Error in browser simulation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_browser_simulation()
