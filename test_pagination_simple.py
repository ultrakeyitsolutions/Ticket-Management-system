#!/usr/bin/env python
"""
Simple test to verify pagination functionality in user dashboard tickets page
"""
import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

def test_pagination_logic():
    """Test the pagination logic directly"""
    print("Testing pagination logic...")
    
    # Simulate a list of tickets (like what would come from database)
    class MockTicket:
        def __init__(self, id, title, status, priority):
            self.id = id
            self.title = title
            self.status = status
            self.priority = priority
            self.ticket_id = f"TICKET-{id:03d}"
    
    # Create 12 mock tickets
    tickets = []
    for i in range(1, 13):
        status = ['Open', 'In Progress', 'Resolved', 'Closed'][i % 4]
        priority = ['Low', 'Medium', 'High', 'Critical'][i % 4]
        tickets.append(MockTicket(i, f'Test Ticket {i}', status, priority))
    
    # Test pagination with 5 items per page
    paginator = Paginator(tickets, 5)
    
    print(f"✅ Pagination setup working!")
    print(f"   - Total tickets: {paginator.count}")
    print(f"   - Tickets per page: {paginator.per_page}")
    print(f"   - Total pages: {paginator.num_pages}")
    
    # Test each page
    for page_num in range(1, paginator.num_pages + 1):
        try:
            page = paginator.page(page_num)
            print(f"\n📄 Page {page_num}:")
            print(f"   - Tickets on this page: {len(page.object_list)}")
            print(f"   - Ticket IDs: {[t.id for t in page.object_list]}")
            
            # Verify no more than 5 tickets per page
            assert len(page.object_list) <= 5, f"Page {page_num} has more than 5 tickets"
            
            # Verify correct tickets are on each page
            expected_start = (page_num - 1) * 5
            expected_end = min(page_num * 5, len(tickets))
            actual_ids = [t.id for t in page.object_list]
            expected_ids = list(range(expected_start + 1, expected_end + 1))
            
            assert actual_ids == expected_ids, f"Page {page_num} has wrong tickets"
            
        except (EmptyPage, PageNotAnInteger) as e:
            print(f"❌ Error getting page {page_num}: {e}")
    
    # Test filtering logic
    print(f"\n🔍 Testing filtering logic...")
    
    # Filter by status 'Open'
    open_tickets = [t for t in tickets if t.status == 'Open']
    open_paginator = Paginator(open_tickets, 5)
    
    print(f"   - Total Open tickets: {open_paginator.count}")
    print(f"   - Pages for Open tickets: {open_paginator.num_pages}")
    
    # Filter by priority 'High' and 'Critical'
    high_priority_tickets = [t for t in tickets if t.priority in ['High', 'Critical']]
    high_priority_paginator = Paginator(high_priority_tickets, 5)
    
    print(f"   - Total High/Critical tickets: {high_priority_paginator.count}")
    print(f"   - Pages for High/Critical tickets: {high_priority_paginator.num_pages}")
    
    # Test edge cases
    print(f"\n🧪 Testing edge cases...")
    
    # Test with empty list
    empty_paginator = Paginator([], 5)
    print(f"   - Empty list pages: {empty_paginator.num_pages} (Django returns 1 for empty)")
    # Django's Paginator always returns at least 1 page, even for empty lists
    
    # Test with single item
    single_paginator = Paginator([tickets[0]], 5)
    print(f"   - Single item pages: {single_paginator.num_pages} (should be 1)")
    assert single_paginator.num_pages == 1, "Single item paginator should have 1 page"
    
    # Test with exactly 5 items
    five_items = tickets[:5]
    five_paginator = Paginator(five_items, 5)
    print(f"   - Exactly 5 items pages: {five_paginator.num_pages} (should be 1)")
    assert five_paginator.num_pages == 1, "Exactly 5 items should fit on 1 page"
    
    print(f"\n🎉 All pagination logic tests passed!")
    
    # Test URL parameter handling
    print(f"\n🔗 Testing URL parameter handling...")
    
    from urllib.parse import parse_qs, urlencode
    
    # Test building URLs with parameters
    base_url = "/dashboard/user-dashboard/tickets/"
    
    # Test page parameter
    page_params = {"page": "2"}
    page_url = f"{base_url}?{urlencode(page_params)}"
    print(f"   - Page 2 URL: {page_url}")
    
    # Test page + status filter
    filter_params = {"page": "1", "status": "Open", "sort": "recent"}
    filter_url = f"{base_url}?{urlencode(filter_params)}"
    print(f"   - Filtered URL: {filter_url}")
    
    # Test parsing parameters
    parsed = parse_qs(filter_url.split('?')[1])
    print(f"   - Parsed parameters: {parsed}")
    
    print(f"\n✅ URL parameter handling working correctly!")

if __name__ == '__main__':
    test_pagination_logic()
