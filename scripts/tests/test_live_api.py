#!/usr/bin/env python
import requests
import json

# Test the live API endpoint
try:
    response = requests.get('http://localhost:8000/api/agents/', timeout=5)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Total agents: {data.get('total', 0)}")
        
        # Find Pranav
        pranav_found = False
        for agent in data.get('results', []):
            if 'pranav' in agent.get('username', '').lower():
                print(f"\nFound Pranav:")
                print(f"  Username: {agent.get('username')}")
                print(f"  Name: {agent.get('name')}")
                print(f"  assigned_tickets_count: {agent.get('assigned_tickets_count')}")
                print(f"  Role: {agent.get('role')}")
                pranav_found = True
                break
        
        if not pranav_found:
            print("\nPranav not found in live API!")
            print("First 5 agents:")
            for i, agent in enumerate(data.get('results', [])[:5]):
                print(f"  {i+1}. {agent.get('username')} - tickets: {agent.get('assigned_tickets_count')}")
    else:
        print(f"Error: {response.text}")
        
except requests.exceptions.RequestException as e:
    print(f"Request failed: {e}")
