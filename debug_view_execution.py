#!/usr/bin/env python
import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth.models import User
from apps.dashboards.views import agent_dashboard_page

def debug_view_execution():
    print("=== Debug View Execution ===")
    
    # Create a mock request
    factory = RequestFactory()
    
    # Get the agent user
    agent_user = User.objects.filter(username='yash').first()
    if not agent_user:
        print("Agent user not found")
        return
    
    # Create request
    request = factory.get('/dashboard/agent-dashboard/reports.html')
    request.user = agent_user
    
    print(f"Testing with user: {agent_user.username}")
    print(f"Request path: {request.path}")
    
    # Test different page parameters
    test_pages = ['reports.html', 'reports', 'reports.html/']
    
    for page in test_pages:
        print(f"\n--- Testing with page: '{page}' ---")
        
        try:
            # Create new request for each test
            request = factory.get(f'/dashboard/agent-dashboard/{page}')
            request.user = agent_user
            
            response = agent_dashboard_page(request, page)
            
            if response.status_code == 200:
                print(f"✅ Page '{page}' loads successfully")
                
                # Check if context contains report data
                if hasattr(response, 'context_data') and response.context_data:
                    context = response.context_data
                    
                    # Check for priority data
                    priority_json = context.get('agent_report_priority_counts_json')
                    if priority_json:
                        print(f"✅ Priority data found: {priority_json}")
                    else:
                        print("❌ Priority data not found")
                    
                    # Check for total tickets
                    total_tickets = context.get('agent_report_total_tickets')
                    if total_tickets is not None:
                        print(f"✅ Total tickets found: {total_tickets}")
                    else:
                        print("❌ Total tickets not found")
                        
                else:
                    print("❌ No context data available")
            else:
                print(f"❌ Page '{page}' failed with status: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error with page '{page}': {e}")

if __name__ == "__main__":
    debug_view_execution()
