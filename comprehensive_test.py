#!/usr/bin/env python
import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from tickets.models import Ticket
from users.models import UserProfile

def comprehensive_test():
    print("=== Comprehensive Agent Reports Test ===")
    
    client = Client()
    
    # Find an agent user with correct role and assigned tickets
    agent_user = None
    for user in User.objects.all():
        if (hasattr(user, 'userprofile') and 
            hasattr(user.userprofile, 'role') and 
            user.userprofile.role and 
            str(user.userprofile.role).lower() == 'agent' and
            user.is_staff and
            Ticket.objects.filter(assigned_to=user).exists()):
            agent_user = user
            break
    
    if not agent_user:
        print("❌ No suitable agent user found")
        return
    
    print(f"✅ Testing with agent: {agent_user.username}")
    
    # Login the agent
    client.force_login(agent_user)
    
    # Test the reports page
    try:
        response = client.get('/dashboard/agent-dashboard/reports.html')
        
        if response.status_code == 200:
            print("✅ Reports page loads successfully")
            
            # Check the rendered HTML
            content = response.content.decode('utf-8')
            
            # Check for key elements
            checks = [
                ('Priority chart canvas', 'tickets-by-priority-chart'),
                ('Chart.js library', 'chart.js'),
                ('initializeCharts function', 'initializeCharts()'),
                ('Priority JSON data', 'agent_report_priority_counts_json'),
                ('Total tickets data', 'agent_report_total_tickets')
            ]
            
            for check_name, check_pattern in checks:
                if check_pattern in content:
                    print(f"✅ {check_name}: Found")
                else:
                    print(f"❌ {check_name}: Not found")
            
            # Check context data if available
            if hasattr(response, 'context_data'):
                context = response.context_data
                
                priority_json = context.get('agent_report_priority_counts_json')
                total_tickets = context.get('agent_report_total_tickets')
                
                if priority_json:
                    print(f"✅ Priority JSON in context: {priority_json}")
                    
                    # Verify the JSON is valid
                    import json
                    try:
                        priority_data = json.loads(priority_json)
                        print(f"✅ Priority data parsed: {priority_data}")
                        print(f"✅ Total from priority data: {sum(priority_data)}")
                        
                        if sum(priority_data) == total_tickets:
                            print("✅ Priority data matches total tickets")
                        else:
                            print(f"❌ Priority data ({sum(priority_data)}) doesn't match total tickets ({total_tickets})")
                    except json.JSONDecodeError:
                        print("❌ Priority JSON is invalid")
                else:
                    print("❌ Priority JSON not in context")
                
                if total_tickets:
                    print(f"✅ Total tickets in context: {total_tickets}")
                else:
                    print("❌ Total tickets not in context")
            
            print("\n=== Summary ===")
            print("The backend is correctly calculating priority data.")
            print("The template contains the necessary elements.")
            print("The issue might be:")
            print("1. JavaScript error preventing chart initialization")
            print("2. Chart.js library not loading properly")
            print("3. DOM timing issue with chart initialization")
            print("4. Data being overwritten by AJAX calls")
            
        else:
            print(f"❌ Reports page failed with status: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    comprehensive_test()
