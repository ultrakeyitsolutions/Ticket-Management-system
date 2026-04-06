#!/usr/bin/env python
"""
Test script to verify agent profile password change functionality
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
from tickets.models import Ticket

def test_agent_password_change():
    """Test agent profile password change functionality"""
    print("Testing agent profile password change functionality...")
    
    try:
        # Get or create an agent user
        agent_user, created = User.objects.get_or_create(
            username='testagent',
            defaults={
                'email': 'agent@tickethub.com',
                'first_name': 'Test',
                'last_name': 'Agent',
                'is_staff': True
            }
        )
        
        if created:
            agent_user.set_password('agent123')
            agent_user.save()
            print(f"📝 Created agent user: {agent_user.username}")
        else:
            print(f"👤 Using existing agent user: {agent_user.username}")
        
        # Get or create user profile with agent role
        profile, created = UserProfile.objects.get_or_create(user=agent_user)
        
        if created:
            # Get agent role
            from users.models import Role
            agent_role, _ = Role.objects.get_or_create(name='Agent')
            profile.role = agent_role
            profile.save()
            print(f"📝 Created agent profile")
        
        print(f"🔐 Current password: agent123")
        print(f"📧 Email: {agent_user.email}")
        print(f"👥 Role: {profile.role.name if profile.role else 'None'}")
        
        # Create test client
        client = Client()
        
        # Login as agent
        login_success = client.login(username='testagent', password='agent123')
        if not login_success:
            print("❌ Agent login failed.")
            return
        
        print(f"✅ Agent logged in successfully")
        
        # Test agent profile page access

        response = client.get('/dashboard/agent-dashboard/profile/')
        
        if response.status_code == 200:
            print(f"✅ Agent profile page accessible (status: {response.status_code})")
        else:
            print(f"❌ Agent profile page not accessible (status: {response.status_code})")
            return
        
        # Check if password change form is present
        content = response.content.decode('utf-8')
        
        if 'password' in content.lower():
            print(f"✅ Password change form found in template")
        else:
            print(f"❌ Password change form not found in template")
        
        if 'Update Security' in content:
            print(f"✅ Update Security button found")
        else:
            print(f"❌ Update Security button not found")
        
        # Test password change
        print(f"\n🔄 Testing password change...")
        
        # Check current password timestamp
        old_password_last_changed = profile.password_last_changed
        print(f"📅 Old password last changed: {old_password_last_changed}")
        
        # Submit password change form
        password_data = {
            'action': 'password',
            'password': 'newagent123',
            'confirm': 'newagent123'
        }
        
        response = client.post('/dashboard/agent-dashboard/profile/', password_data)
        
        if response.status_code == 200:
            print(f"✅ Password form submitted successfully (status: {response.status_code})")
        else:
            print(f"❌ Password form submission failed (status: {response.status_code})")
            return
        
        # Check if password was actually changed
        agent_user.refresh_from_db()
        profile.refresh_from_db()
        
        # Test new password
        new_password_works = client.login(username='testagent', password='newagent123')
        old_password_works = client.login(username='testagent', password='agent123')
        
        if new_password_works and not old_password_works:
            print(f"✅ Password changed successfully!")
            print(f"✅ New password works: {new_password_works}")
            print(f"✅ Old password doesn't work: {not old_password_works}")
        else:
            print(f"❌ Password change failed")
            print(f"❌ New password works: {new_password_works}")
            print(f"❌ Old password still works: {old_password_works}")
        
        # Check if timestamp was updated
        new_password_last_changed = profile.password_last_changed
        print(f"📅 New password last changed: {new_password_last_changed}")
        
        if new_password_last_changed != old_password_last_changed:
            print(f"✅ Password timestamp updated successfully!")
        else:
            print(f"❌ Password timestamp not updated")
        
        # Check for password error message
        content = response.content.decode('utf-8')
        if 'password_error' in content:
            print(f"❌ Password error found in response")
        else:
            print(f"✅ No password errors in response")
        
        # Check for password saved message
        if 'Password updated' in content or 'password_saved' in content:
            print(f"✅ Password saved message found")
        else:
            print(f"❌ Password saved message not found")
        
        # Test password mismatch
        print(f"\n❌ Testing password mismatch...")
        
        mismatch_data = {
            'action': 'password',
            'password': 'mismatch123',
            'confirm': 'different123'
        }
        
        response = client.post('/dashboard/agent-dashboard/profile/', mismatch_data)
        
        if response.status_code == 200:
            print(f"✅ Mismatch form submitted successfully")
            
            content = response.content.decode('utf-8')
            if 'Passwords do not match' in content:
                print(f"✅ Password mismatch error displayed correctly")
            else:
                print(f"❌ Password mismatch error not displayed")
        else:
            print(f"❌ Mismatch form submission failed")
        
        # Reset password for future tests
        agent_user.set_password('agent123')
        agent_user.save()
        print(f"\n🔄 Reset password to agent123 for future tests")
        
        print(f"\n🎉 Agent password change test completed!")
        
    except Exception as e:
        print(f"❌ Error testing agent password change: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_agent_password_change()
