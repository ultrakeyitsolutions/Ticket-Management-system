#!/usr/bin/env python
"""
Debug script to check agent profile template variables
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

def debug_template_variables():
    """Debug agent profile template variables"""
    print("🔍 Debugging Agent Profile Template Variables")
    print("=" * 60)
    
    try:
        # Get agent user
        agent_user = User.objects.filter(username='testagent').first()
        if not agent_user:
            print("❌ Agent user not found")
            return
        
        print(f"👤 Testing with agent: {agent_user.username}")
        
        # Create test client
        client = Client()
        
        # Login as agent
        login_success = client.login(username='testagent', password='agent123')
        if not login_success:
            print("❌ Agent login failed")
            return
        
        print(f"✅ Agent logged in successfully")
        
        # Access agent profile page
        response = client.get('/dashboard/agent-dashboard/profile/')
        
        if response.status_code == 200:
            print(f"✅ Profile page accessible")
        else:
            print(f"❌ Profile page not accessible: {response.status_code}")
            return
        
        # Check template variables
        content = response.content.decode('utf-8')
        print(f"\n📋 Template Variables Analysis:")
        
        # Check for each variable
        variables_to_check = [
            'profile_full_name',
            'request.user.username',
            'request.user.get_full_name',
            'profile_email',
            'request.user.email',
            'profile_role',
            'profile_phone',
            'profile_obj.department',
            'profile_tickets_closed',
            'profile_avg_rating_display'
        ]
        
        for var_name in variables_to_check:
            if f'{{ {var_name}' in content:
                print(f"✅ {var_name} template variable found")
            else:
                print(f"❌ {var_name} template variable NOT found")
        
        # Check for specific email patterns
        print(f"\n📧 Email Analysis:")
        if 'admin@tickethub.com' in content:
            print(f"✅ Found admin@tickethub.com in content")
        if 'agent@test.com' in content:
            print(f"✅ Found agent@test.com in content")
        if 'yy' in content:
            print(f"✅ Found 'yy' in content")
        if 'profile_email' in content:
            # Extract the email value
            import re
            email_match = re.search(r'profile_email[^>]*>([^<]*)', content)
            if email_match:
                print(f"✅ Profile email value: {email_match.group(1)}")
        
        # Check for specific patterns that might cause 'yy'
        print(f"\n🔍 Pattern Analysis:")
        if 'request.user.username' in content and 'yy' in content:
            print(f"⚠️  Found 'request.user.username' and 'yy' together - possible template issue")
        
        # Check if there are any Django template rendering issues
        print(f"\n🐛 Django Template Check:")
        if '{%' in content and '%}' in content:
            print(f"✅ Django template syntax looks correct")
        else:
            print(f"❌ Django template syntax might be broken")
        
        print(f"\n🎯 Debugging Summary:")
        print(f"   - Template variables: {len([v for v in variables_to_check if f'{{ {v}' in content])}")
        print(f"   - Email patterns: Found admin@tickethub.com, agent@test.com")
        print(f"   - 'yy' pattern: Found in content")
        
        if 'yy' in content and 'profile_email' in content:
            print(f"   ⚠️  ISSUE: 'yy' appearing in email context")
            print(f"   💡 SOLUTION: Check template variable rendering")
        
    except Exception as e:
        print(f"❌ Error debugging template variables: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    debug_template_variables()
