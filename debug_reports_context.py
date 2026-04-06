#!/usr/bin/env python
import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User

def debug_reports_context():
    print("=== Debug Reports Context ===")
    
    client = Client()
    
    # Find an agent user
    agent_user = User.objects.filter(username='yash').first()
    if not agent_user:
        print("Agent user 'yash' not found")
        return
    
    print(f"Testing with agent: {agent_user.username}")
    client.force_login(agent_user)
    
    # Test the reports page with debug
    try:
        response = client.get('/dashboard/agent-dashboard/reports.html')
        
        if response.status_code == 200:
            print("✅ Page loads successfully")
            
            # Check context data (may not be available in test client)
            context_available = False
            if hasattr(response, 'context_data') and response.context_data:
                context = response.context_data
                context_available = True
                print(f"Context keys: {list(context.keys())}")
            else:
                print("Context data not available in test client")
            
            # Check the rendered HTML content instead
            content = response.content.decode('utf-8')
            
            # Look for the actual data in the HTML
            print("\n=== Checking Rendered HTML ===")
            
            # Check for priority data
            if 'agent_report_priority_counts_json' in content:
                print("✅ Priority JSON variable found in template")
                
                # Try to extract the actual value
                import re
                pattern = r'agent_report_priority_counts_json.*?(\[.*?\])'
                match = re.search(pattern, content)
                if match:
                    priority_value = match.group(1)
                    print(f"✅ Priority value extracted: {priority_value}")
                else:
                    print("❌ Could not extract priority value")
            else:
                print("❌ Priority JSON variable not found in template")
            
            # Check for total tickets
            if 'agent_report_total_tickets' in content:
                print("✅ Total tickets variable found in template")
                
                # Try to extract the actual value
                pattern = r'agent_report_total_tickets.*?(\d+)'
                match = re.search(pattern, content)
                if match:
                    total_value = match.group(1)
                    print(f"✅ Total tickets value extracted: {total_value}")
                else:
                    print("❌ Could not extract total tickets value")
            else:
                print("❌ Total tickets variable not found in template")
            
            # Check for user name
            if 'agent_report_user_name' in content:
                print("✅ User name variable found in template")
            else:
                print("❌ User name variable not found in template")
                
        else:
            print(f"❌ Error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_reports_context()
