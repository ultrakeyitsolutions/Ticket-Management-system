#!/usr/bin/env python
import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from tickets.models import Ticket

def test_agent_with_correct_role():
    print("=== Testing Agent with Correct Role ===")
    
    client = Client()
    
    # Find an agent user with assigned tickets and correct role
    agent_user = None
    for user in User.objects.all():
        # Check if user is agent (has Agent role profile and is_staff)
        if (hasattr(user, 'userprofile') and 
            hasattr(user.userprofile, 'role') and 
            user.userprofile.role and 
            str(user.userprofile.role).lower() == 'agent' and
            Ticket.objects.filter(assigned_to=user).exists()):
            agent_user = user
            break
    
    if not agent_user:
        print("No agent users with assigned tickets found")
        return
    
    print(f"Testing with agent: {agent_user.username}")
    print(f"  is_staff: {agent_user.is_staff}")
    print(f"  Profile role: {agent_user.userprofile.role}")
    
    # Login the agent
    client.force_login(agent_user)
    
    # Test the reports page
    try:
        response = client.get('/dashboard/agent-dashboard/reports.html')
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Reports page loads successfully")
            
            # Check context data
            if hasattr(response, 'context_data'):
                context = response.context_data
                
                priority_json = context.get('agent_report_priority_counts_json', 'NOT FOUND')
                total_tickets = context.get('agent_report_total_tickets', 'NOT FOUND')
                print(f"Priority JSON: {priority_json}")
                print(f"Total tickets: {total_tickets}")
                
                # Check if the data makes sense
                if priority_json != 'NOT FOUND':
                    import json
                    try:
                        priority_data = json.loads(priority_json)
                        print(f"Priority data: {priority_data}")
                        print(f"Sum: {sum(priority_data)}")
                        
                        if sum(priority_data) == total_tickets:
                            print("✅ Priority data matches total tickets")
                        else:
                            print("❌ Priority data doesn't match total tickets")
                    except json.JSONDecodeError:
                        print("❌ Priority JSON is invalid")
                else:
                    print("❌ Priority data not found")
            
        elif response.status_code == 302:
            print("❌ Redirected")
            print(f"Redirect to: {response.get('Location', 'Unknown')}")
        else:
            print(f"❌ Error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_agent_with_correct_role()
