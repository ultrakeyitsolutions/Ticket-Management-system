#!/usr/bin/env python
"""
Test script to verify ticket filtering functionality
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth.models import User
from tickets.models import Ticket

def test_ticket_filtering():
    """Test the ticket filtering functionality"""
    print("Testing ticket filtering functionality...")
    
    # Create a test user
    user = User.objects.create_user(
        username='filtertest',
        email='filtertest@example.com',
        password='testpass123'
    )
    
    # Create test tickets with different statuses
    statuses = ['Open', 'In Progress', 'Resolved', 'Closed']
    priorities = ['Low', 'Medium', 'High', 'Critical']
    
    tickets = []
    for i in range(20):  # Create 20 tickets
        ticket = Ticket.objects.create(
            title=f'Filter Test Ticket {i+1}',
            description=f'Description for ticket {i+1}',
            created_by=user,
            status=statuses[i % 4],
            priority=priorities[i % 4]
        )
        tickets.append(ticket)
    
    # Import the view function
    from dashboards.views import user_dashboard_page
    
    factory = RequestFactory()
    
    # Test filtering by status
    test_cases = [
        ('all', 'All tickets'),
        ('Open', 'Open tickets only'),
        ('In Progress', 'In Progress tickets only'),
        ('Resolved', 'Resolved tickets only'),
        ('Closed', 'Closed tickets only')
    ]
    
    for status_filter, description in test_cases:
        print(f"\n🔍 Testing {description}...")
        
        # Create request with status filter
        request = factory.get(f'/dashboard/user-dashboard/tickets/?status={status_filter}')
        request.user = user
        
        try:
            response = user_dashboard_page(request, 'tickets')
            
            if hasattr(response, 'context_data'):
                context = response.context_data
                if 'paginator' in context:
                    paginator = context['paginator']
                    current_filter = context.get('current_status_filter', 'all')
                    
                    print(f"   - Current filter: {current_filter}")
                    print(f"   - Total tickets: {paginator.count}")
                    
                    # Verify filter was applied correctly
                    if status_filter == 'all':
                        expected_count = 20  # All tickets
                    else:
                        # Count tickets with the specific status
                        expected_count = Ticket.objects.filter(created_by=user, status=status_filter).count()
                    
                    print(f"   - Expected count: {expected_count}")
                    
                    if paginator.count == expected_count:
                        print(f"   ✅ {description} - PASSED")
                    else:
                        print(f"   ❌ {description} - FAILED (Expected {expected_count}, got {paginator.count})")
                    
                    # Verify current filter context
                    if current_filter == status_filter:
                        print(f"   ✅ Filter context correct")
                    else:
                        print(f"   ❌ Filter context wrong (Expected {status_filter}, got {current_filter})")
                        
            else:
                print(f"   ❌ No context data found")
                
        except Exception as e:
            print(f"   ❌ Error testing {description}: {e}")
    
    # Test sorting functionality
    print(f"\n📊 Testing sorting functionality...")
    
    sort_test_cases = [
        ('recent', 'Newest first'),
        ('oldest', 'Oldest first'),
        ('priority', 'Highest priority')
    ]
    
    for sort_filter, description in sort_test_cases:
        print(f"\n📊 Testing {description}...")
        
        request = factory.get(f'/dashboard/user-dashboard/tickets/?sort={sort_filter}')
        request.user = user
        
        try:
            response = user_dashboard_page(request, 'tickets')
            
            if hasattr(response, 'context_data'):
                context = response.context_data
                if 'tickets' in context:
                    tickets = context['tickets']
                    current_sort = context.get('current_sort_filter', 'recent')
                    
                    print(f"   - Current sort: {current_sort}")
                    print(f"   - Tickets returned: {len(tickets)}")
                    print(f"   - First ticket: {tickets[0].title if tickets else 'None'}")
                    
                    # Verify sort context
                    if current_sort == sort_filter:
                        print(f"   ✅ Sort context correct")
                    else:
                        print(f"   ❌ Sort context wrong (Expected {sort_filter}, got {current_sort})")
                        
        except Exception as e:
            print(f"   ❌ Error testing {description}: {e}")
    
    # Test combined filtering and sorting
    print(f"\n🔀 Testing combined filtering and sorting...")
    
    request = factory.get('/dashboard/user-dashboard/tickets/?status=Open&sort=priority')
    request.user = user
    
    try:
        response = user_dashboard_page(request, 'tickets')
        
        if hasattr(response, 'context_data'):
            context = response.context_data
            if 'paginator' in context:
                paginator = context['paginator']
                current_status = context.get('current_status_filter', 'all')
                current_sort = context.get('current_sort_filter', 'recent')
                
                print(f"   - Status filter: {current_status}")
                print(f"   - Sort filter: {current_sort}")
                print(f"   - Open tickets with priority sort: {paginator.count}")
                
                # Expected: Open tickets only (5 of them)
                expected_open = Ticket.objects.filter(created_by=user, status='Open').count()
                
                if paginator.count == expected_open and current_status == 'Open' and current_sort == 'priority':
                    print(f"   ✅ Combined filtering and sorting - PASSED")
                else:
                    print(f"   ❌ Combined filtering and sorting - FAILED")
                    
    except Exception as e:
        print(f"   ❌ Error testing combined filters: {e}")
    
    # Clean up
    Ticket.objects.filter(created_by=user).delete()
    user.delete()
    
    print(f"\n🎉 All filtering tests completed!")

if __name__ == '__main__':
    test_ticket_filtering()
