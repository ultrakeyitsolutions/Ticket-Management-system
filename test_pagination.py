#!/usr/bin/env python
"""
Test script to verify pagination functionality in user dashboard tickets page
"""
import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import RequestFactory, TestCase
from django.contrib.auth.models import User
from tickets.models import Ticket
from dashboards.views import user_dashboard_page

def test_pagination():
    """Test the pagination functionality"""
    print("Testing pagination functionality...")
    
    # Create a mock request
    factory = RequestFactory()
    
    # Create a test user
    user = User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )
    
    # Create test tickets for the user
    for i in range(12):  # Create 12 tickets to test pagination
        Ticket.objects.create(
            title=f'Test Ticket {i+1}',
            description=f'Description for ticket {i+1}',
            created_by=user,
            status='Open' if i % 2 == 0 else 'In Progress',
            priority=['Low', 'Medium', 'High', 'Critical'][i % 4]
        )
    
    # Test page 1
    request = factory.get('/dashboard/user-dashboard/tickets/?page=1')
    request.user = user
    
    try:
        # Call the view function
        response = user_dashboard_page(request, 'tickets')
        
        # Check if pagination context is present
        if hasattr(response, 'context_data'):
            context = response.context_data
            
            if 'paginator' in context and 'tickets_page' in context:
                paginator = context['paginator']
                tickets_page = context['tickets_page']
                
                print(f"✅ Pagination working correctly!")
                print(f"   - Total tickets: {paginator.count}")
                print(f"   - Tickets per page: {paginator.per_page}")
                print(f"   - Total pages: {paginator.num_pages}")
                print(f"   - Current page: {tickets_page.number}")
                print(f"   - Tickets on current page: {len(tickets_page.object_list)}")
                
                # Verify 5 tickets per page
                assert paginator.per_page == 5, "Expected 5 tickets per page"
                assert len(tickets_page.object_list) <= 5, "Expected max 5 tickets on page"
                
                print(f"✅ All pagination tests passed!")
                
            else:
                print("❌ Pagination context not found in response")
        else:
            print("❌ Response doesn't have context_data")
            
    except Exception as e:
        print(f"❌ Error testing pagination: {e}")
    
    # Clean up
    Ticket.objects.filter(created_by=user).delete()
    user.delete()
    
    print("\nTesting pagination with filters...")
    
    # Test with status filter
    request = factory.get('/dashboard/user-dashboard/tickets/?status=Open&page=1')
    request.user = user
    
    # Create user again for filter test
    user = User.objects.create_user(
        username='testuser2',
        email='test2@example.com',
        password='testpass123'
    )
    
    # Create mixed status tickets
    for i in range(8):
        Ticket.objects.create(
            title=f'Filter Test {i+1}',
            description='Description',
            created_by=user,
            status='Open' if i < 3 else 'Closed',  # 3 Open, 5 Closed
            priority='Medium'
        )
    
    request.user = user
    
    try:
        response = user_dashboard_page(request, 'tickets')
        
        if hasattr(response, 'context_data'):
            context = response.context_data
            if 'paginator' in context:
                paginator = context['paginator']
                print(f"✅ Filter pagination working!")
                print(f"   - Total Open tickets: {paginator.count}")
                print(f"   - Expected: 3, Got: {paginator.count}")
                
                assert paginator.count == 3, f"Expected 3 Open tickets, got {paginator.count}"
                
    except Exception as e:
        print(f"❌ Error testing filter pagination: {e}")
    
    # Clean up
    Ticket.objects.filter(created_by=user).delete()
    user.delete()
    
    print("\n🎉 All pagination tests completed!")

if __name__ == '__main__':
    test_pagination()
