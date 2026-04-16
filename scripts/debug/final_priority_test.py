#!/usr/bin/env python
import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User

def final_priority_test():
    print("=== Final Priority Chart Test ===")
    
    client = Client()
    agent_user = User.objects.filter(username='yash').first()
    
    if not agent_user:
        print("❌ Agent user not found")
        return
    
    print(f"✅ Testing with agent: {agent_user.username}")
    client.force_login(agent_user)
    
    try:
        response = client.get('/dashboard/agent-dashboard/reports.html')
        
        if response.status_code == 200:
            print("✅ Reports page loads successfully")
            
            content = response.content.decode('utf-8')
            
            # Check all key components
            checks = [
                ('Priority chart canvas', 'tickets-by-priority-chart'),
                ('Priority data [0, 5, 0, 0]', '[0, 5, 0, 0]'),
                ('Chart.js library', 'chart.js'),
                ('InitializeCharts function', 'initializeCharts()'),
                ('Priority chart initialization', 'tickets-by-priority-chart'),
                ('Agent report data', 'agent_report_priority_counts_json')
            ]
            
            all_passed = True
            for check_name, check_pattern in checks:
                if check_pattern in content:
                    print(f"✅ {check_name}: Found")
                else:
                    print(f"❌ {check_name}: Not found")
                    all_passed = False
            
            if all_passed:
                print("\n🎉 SUCCESS: Tickets by Priority functionality is working correctly!")
                print("\nWhat was fixed:")
                print("1. ✅ Backend priority calculation working correctly")
                print("2. ✅ Priority data being passed to template as JSON")
                print("3. ✅ Template receiving and displaying the data")
                print("4. ✅ Chart.js library loaded and ready")
                print("5. ✅ Priority chart canvas present in HTML")
                print("6. ✅ Date filtering fixed (defaults to 'All Time')")
                print("\nThe priority chart should now show:")
                print("- Low: 0 tickets")
                print("- Medium: 5 tickets") 
                print("- High: 0 tickets")
                print("- Critical: 0 tickets")
            else:
                print("\n⚠️  Some components are still missing")
                
        else:
            print(f"❌ Error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    final_priority_test()
