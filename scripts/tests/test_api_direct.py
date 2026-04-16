#!/usr/bin/env python
import os
import sys
import django
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import RequestFactory
from users.views import AgentsListView
from django.contrib.auth.models import User

# Create a mock request
factory = RequestFactory()
admin_user = User.objects.filter(is_superuser=True).first()
if not admin_user:
    print("No admin user found!")
    sys.exit(1)

# Test the API
request = factory.get('/api/agents/')
request.user = admin_user

view = AgentsListView()
response = view.get(request)

print(f"Response status: {response.status_code}")
print(f"Response data keys: {list(response.data.keys())}")

# Find Pranav in the response
if 'results' in response.data:
    pranav_found = False
    for agent in response.data['results']:
        if 'pranav' in agent.get('username', '').lower():
            print(f"\nFound Pranav in API response:")
            print(f"  Username: {agent.get('username')}")
            print(f"  Name: {agent.get('name')}")
            print(f"  assigned_tickets_count: {agent.get('assigned_tickets_count')}")
            print(f"  Role: {agent.get('role')}")
            print(f"  Department: {agent.get('department')}")
            pranav_found = True
            break
    
    if not pranav_found:
        print("\nPranav not found in API response!")
        print("First 5 agents in response:")
        for i, agent in enumerate(response.data['results'][:5]):
            print(f"  {i+1}. {agent.get('username')} - assigned_tickets_count: {agent.get('assigned_tickets_count')}")
else:
    print("No 'results' key in response data!")
    print(f"Response data: {response.data}")
