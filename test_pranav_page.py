#!/usr/bin/env python
import requests

# Test with a larger page size to include Pranav
try:
    response = requests.get('http://localhost:8000/api/agents/?page_size=100', timeout=5)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Total agents: {data.get('total', 0)}")
        
        # Find Pranav
        for i, agent in enumerate(data.get('results', [])):
            if 'pranav' in agent.get('username', '').lower():
                print(f"\nFound Pranav at position {i}:")
                print(f"  Username: {agent.get('username')}")
                print(f"  Name: {agent.get('name')}")
                print(f"  assigned_tickets_count: {agent.get('assigned_tickets_count')}")
                print(f"  Role: {agent.get('role')}")
                print(f"  Department: {agent.get('department')}")
                break
    else:
        print(f"Error: {response.text}")
        
except requests.exceptions.RequestException as e:
    print(f"Request failed: {e}")
