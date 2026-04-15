#!/usr/bin/env python
import requests
import json

# Test with authentication - first get a login token
try:
    # Try to login first
    login_data = {
        'username': 'admin',  # Try common admin credentials
        'password': 'admin'
    }
    
    session = requests.Session()
    login_response = session.post('http://localhost:8000/users/login/', data=login_data, timeout=5)
    print(f"Login Status: {login_response.status_code}")
    
    # Now test the API
    response = session.get('http://localhost:8000/api/agents/', timeout=5)
    print(f"API Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Total agents: {data.get('total', 0)}")
        
        # Find Pranav
        for agent in data.get('results', []):
            if 'pranav' in agent.get('username', '').lower():
                print(f"\nFound Pranav:")
                print(f"  Username: {agent.get('username')}")
                print(f"  Name: {agent.get('name')}")
                print(f"  assigned_tickets_count: {agent.get('assigned_tickets_count')}")
                print(f"  Role: {agent.get('role')}")
                print(f"  Department: {agent.get('department')}")
                break
    else:
        print(f"API Error: {response.text}")
        
except requests.exceptions.RequestException as e:
    print(f"Request failed: {e}")
