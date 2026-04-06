#!/usr/bin/env python
import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from tickets.models import Ticket

def test_agent_reports_view():
    print("=== Testing Agent Reports View ===")
    
    client = Client()
    
    # Find a user with assigned tickets
    user = None
    for u in User.objects.all():
        if Ticket.objects.filter(assigned_to=u).exists():
            user = u
            break
    
    if not user:
        print("No users with assigned tickets found")
        return
    
    print(f"Testing with user: {user.username}")
    
    # Login the user
    client.force_login(user)
    
    # Test the reports page
    try:
        response = client.get('/dashboard/agent-dashboard/reports.html')
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Reports page loads successfully")
            
            # Check if the response contains priority data
            content = response.content.decode('utf-8')
            
            # Look for priority chart canvas
            if 'tickets-by-priority-chart' in content:
                print("✅ Priority chart canvas found in template")
            else:
                print("❌ Priority chart canvas not found")
            
            # Look for priority data in context (if it's a template response)
            if hasattr(response, 'context_data'):
                context = response.context_data
                priority_json = context.get('agent_report_priority_counts_json', 'NOT FOUND')
                print(f"Priority JSON in context: {priority_json}")
                
                total_tickets = context.get('agent_report_total_tickets', 'NOT FOUND')
                print(f"Total tickets in context: {total_tickets}")
            
        elif response.status_code == 302:
            print("❌ Redirected (likely not authenticated or wrong role)")
            print(f"Redirect to: {response.get('Location', 'Unknown')}")
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Content: {response.content.decode('utf-8')[:500]}...")
            
    except Exception as e:
        print(f"❌ Error testing view: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_agent_reports_view()
