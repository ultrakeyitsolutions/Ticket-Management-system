#!/usr/bin/env python
"""
Direct test of the skills functionality without authentication
"""
import os
import sys
import django
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.contrib.auth.models import User
from users.models import UserProfile, Role
from dashboards.views import save_skills, get_skills
from django.test import RequestFactory
from django.contrib.messages.storage.fallback import FallbackStorage

def test_skills_directly():
    print("Testing Skills functionality directly...")
    
    # Get the test agent user
    try:
        user = User.objects.get(username='testagent')
        print(f"Using test agent: {user.username}")
    except User.DoesNotExist:
        print("Test agent user not found!")
        return
    
    # Create request factory
    factory = RequestFactory()
    
    # Test GET skills
    print("\n1. Testing GET skills...")
    request = factory.get('/dashboard/agent-dashboard/get-skills/')
    request.user = user
    
    # Add session and messages
    request.session = {}
    request._messages = FallbackStorage(request)
    
    response = get_skills(request)
    print(f"Status code: {response.status_code}")
    
    if response.status_code == 200:
        data = json.loads(response.content.decode())
        print(f"Response: {data}")
        if data.get('success'):
            print(f"✓ Skills loaded successfully: {data.get('skills', [])}")
        else:
            print(f"✗ Error in response: {data.get('message')}")
    else:
        print(f"✗ Failed to get skills")
    
    # Test POST skills
    print("\n2. Testing POST skills...")
    new_skills = ['Python', 'Django', 'JavaScript', 'React', 'Node.js', 'Vue.js']
    
    request = factory.post(
        '/dashboard/agent-dashboard/save-skills/',
        data=json.dumps({'skills': new_skills}),
        content_type='application/json'
    )
    request.user = user
    request.session = {}
    request._messages = FallbackStorage(request)
    
    response = save_skills(request)
    print(f"Status code: {response.status_code}")
    
    if response.status_code == 200:
        data = json.loads(response.content.decode())
        print(f"Response: {data}")
        if data.get('success'):
            print(f"✓ Skills saved successfully!")
        else:
            print(f"✗ Error saving skills: {data.get('message')}")
    else:
        print(f"✗ Failed to save skills")
    
    # Verify skills were saved
    print("\n3. Verifying saved skills...")
    profile = UserProfile.objects.get(user=user)
    if profile.skills:
        saved_skills = json.loads(profile.skills)
        print(f"Skills in database: {saved_skills}")
        print(f"✓ Match expected: {saved_skills == new_skills}")
    else:
        print("✗ No skills found in database")
    
    # Test GET again to verify
    print("\n4. Testing GET skills after save...")
    request = factory.get('/dashboard/agent-dashboard/get-skills/')
    request.user = user
    request.session = {}
    request._messages = FallbackStorage(request)
    
    response = get_skills(request)
    if response.status_code == 200:
        data = json.loads(response.content.decode())
        if data.get('success'):
            final_skills = data.get('skills', [])
            print(f"✓ Final skills: {final_skills}")
            print(f"✓ All tests passed!" if final_skills == new_skills else "✗ Skills mismatch")
    
    print("\nDirect test completed!")

if __name__ == '__main__':
    test_skills_directly()
