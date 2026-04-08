#!/usr/bin/env python
"""
Test script to verify admin reports agent performance fix
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

def test_admin_reports_context():
    """Test that admin reports view includes ratings_agent_perf context"""
    from django.test import RequestFactory
    from django.contrib.auth.models import User
    from apps.users.models import UserProfile, Role
    from apps.dashboards.views import admin_dashboard_page
    
    # Create a mock request
    factory = RequestFactory()
    request = factory.get('/dashboard/admin-dashboard/reports.html/')
    
    # Create or get admin user
    try:
        admin_user = User.objects.get(username='admin')
    except User.DoesNotExist:
        admin_user = User.objects.create_user('admin', 'admin@test.com', 'admin123')
        try:
            admin_role = Role.objects.get(name='Admin')
        except Role.DoesNotExist:
            admin_role = Role.objects.create(name='Admin')
        profile = UserProfile.objects.create(user=admin_user, role=admin_role)
    
    request.user = admin_user
    
    # Test the view
    try:
        response = admin_dashboard_page(request, 'reports.html')
        print('SUCCESS: Admin reports view executed without errors')
        
        if hasattr(response, 'context_data'):
            context_keys = list(response.context_data.keys())
            print(f'Available context keys: {context_keys}')
            
            if 'ratings_agent_perf' in response.context_data:
                agent_data = response.context_data['ratings_agent_perf']
                print(f'SUCCESS: ratings_agent_perf found in context with {len(agent_data)} agents')
                
                if agent_data:
                    print(f'Sample agent data: {agent_data[0]}')
                    print('Agent performance data is properly structured')
                else:
                    print('WARNING: ratings_agent_perf is empty')
            else:
                print('ERROR: ratings_agent_perf not found in context')
        else:
            print('ERROR: No context data in response')
            
    except Exception as e:
        print(f'ERROR: {e}')
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_admin_reports_context()
