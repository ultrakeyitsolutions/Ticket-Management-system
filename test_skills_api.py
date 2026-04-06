#!/usr/bin/env python
"""
Test script to verify the skills API functionality
"""
import os
import sys
import django
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from users.models import UserProfile, Role

def test_skills_api():
    print("Testing Skills API functionality...")
    
    # Create test user and profile if they don't exist
    user, created = User.objects.get_or_create(
        username='testagent',
        defaults={
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'Agent'
        }
    )
    
    if created:
        user.set_password('testpass123')
        user.save()
        print("Created test user")
    
    # Get or create user profile
    agent_role = Role.objects.get(name='Agent')
    profile, created = UserProfile.objects.get_or_create(
        user=user,
        defaults={
            'skills': json.dumps(['Python', 'Django', 'JavaScript']),
            'role': agent_role
        }
    )
    
    if not created:
        profile.skills = json.dumps(['Python', 'Django', 'JavaScript'])
        profile.role = agent_role
        profile.save()
        print("Updated existing profile")
    
    # Create client and login
    client = Client()
    
    # First, get the login page to establish session
    login_response = client.get('/users/login/')
    print(f"Login page status: {login_response.status_code}")
    
    # Now login
    login_success = client.login(username='testagent', password='testpass123')
    print(f"Login successful: {login_success}")
    
    # Check if user is authenticated
    response = client.get('/dashboard/agent-dashboard/')
    print(f"Dashboard access status: {response.status_code}")
    
    # Test GET skills
    print("\n1. Testing GET skills...")
    response = client.get('/dashboard/agent-dashboard/get-skills/')
    print(f"Status code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Response: {data}")
        if data.get('success'):
            print(f"Skills loaded: {data.get('skills', [])}")
        else:
            print(f"Error in response: {data.get('message')}")
    else:
        print(f"Failed to get skills. Content: {response.content.decode()[:200]}...")
    
    # Test POST skills
    print("\n2. Testing POST skills...")
    new_skills = ['Python', 'Django', 'JavaScript', 'React', 'Node.js']
    response = client.post(
        '/dashboard/agent-dashboard/save-skills/',
        data=json.dumps({'skills': new_skills}),
        content_type='application/json'
    )
    print(f"Status code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Response: {data}")
        if data.get('success'):
            print("Skills saved successfully!")
        else:
            print(f"Error saving skills: {data.get('message')}")
    else:
        print(f"Failed to save skills. Content: {response.content.decode()}")
    
    # Verify skills were saved
    print("\n3. Verifying saved skills...")
    profile.refresh_from_db()
    if profile.skills:
        saved_skills = json.loads(profile.skills)
        print(f"Skills in database: {saved_skills}")
        print(f"Match expected: {saved_skills == new_skills}")
    else:
        print("No skills found in database")
    
    print("\nTest completed!")

if __name__ == '__main__':
    test_skills_api()
