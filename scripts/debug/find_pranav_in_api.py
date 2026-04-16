#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import RequestFactory
from users.views import AgentsListView
from django.contrib.auth.models import User

# Create a mock request
factory = RequestFactory()
admin_user = User.objects.filter(is_superuser=True).first()
request = factory.get('/api/agents/?page_size=100')  # Get all agents
request.user = admin_user

view = AgentsListView()
response = view.get(request)

print(f"Total agents in response: {len(response.data.get('results', []))}")
print(f"Total count from API: {response.data.get('total', 0)}")

# Search for Pranav
pranav_found = False
for i, agent in enumerate(response.data.get('results', [])):
    if 'pranav' in agent.get('username', '').lower():
        print(f"\nFound Pranav at position {i}:")
        print(f"  Username: {agent.get('username')}")
        print(f"  Name: {agent.get('name')}")
        print(f"  assigned_tickets_count: {agent.get('assigned_tickets_count')}")
        print(f"  Role: {agent.get('role')}")
        print(f"  Department: {agent.get('department')}")
        pranav_found = True
        break

if not pranav_found:
    print("\nPranav still not found! Let's check all usernames...")
    usernames = [agent.get('username') for agent in response.data.get('results', [])]
    pranav_usernames = [u for u in usernames if 'pranav' in u.lower()]
    print(f"Usernames containing 'pranav': {pranav_usernames}")
    
    # Check if pranav exists in database
    from django.contrib.auth.models import User
    pranav = User.objects.filter(username__icontains='pranav')
    print(f"Pranav users in database: {list(pranav.values_list('username', flat=True))}")
    
    # Check if pranav is an agent
    from users.models import UserProfile
    pranav_with_profile = pranav.select_related('userprofile__role').first()
    if pranav_with_profile and pranav_with_profile.userprofile:
        print(f"Pranav role: {pranav_with_profile.userprofile.role}")
        print(f"Pranav is_active: {pranav_with_profile.userprofile.is_active}")
    else:
        print("Pranav has no userprofile!")
