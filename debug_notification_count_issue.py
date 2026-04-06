#!/usr/bin/env python
"""
Debug why notification count is still showing 4
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.contrib.auth.models import User
from django.test import RequestFactory
from dashboards.views import agent_notifications_api
from tickets.models import ChatMessage, Ticket

def debug_notification_count_issue():
    print("Debugging Notification Count Issue...")
    
    # Get the test agent user
    user = User.objects.get(username='testagent')
    print(f"Using test agent: {user.username}")
    
    # Check ALL notifications in the system
    print(f"\n=== Complete Notification Analysis ===")
    
    # Check unread chat messages
    unread_chat = ChatMessage.objects.filter(recipient=user, is_read=False)
    print(f"Unread chat messages: {unread_chat.count()}")
    
    # Check ALL tickets assigned to user (not just Open/In Progress)
    all_tickets = Ticket.objects.filter(assigned_to=user)
    print(f"All tickets assigned to user: {all_tickets.count()}")
    
    # Check ticket notifications by status
    open_tickets = Ticket.objects.filter(assigned_to=user, status='Open')
    in_progress_tickets = Ticket.objects.filter(assigned_to=user, status='In Progress')
    resolved_tickets = Ticket.objects.filter(assigned_to=user, status='Resolved')
    closed_tickets = Ticket.objects.filter(assigned_to=user, status='Closed')
    
    print(f"\nTicket Status Breakdown:")
    print(f"  Open: {open_tickets.count()}")
    print(f"  In Progress: {in_progress_tickets.count()}")
    print(f"  Resolved: {resolved_tickets.count()}")
    print(f"  Closed: {closed_tickets.count()}")
    
    # Check what the API actually returns
    print(f"\n=== API Response Analysis ===")
    request = RequestFactory().get('/dashboard/agent-dashboard/api/notifications/')
    request.user = user
    
    response = agent_notifications_api(request)
    import json
    data = json.loads(response.content.decode())
    
    print(f"API unread_count: {data.get('unread_count', 0)}")
    print(f"API results count: {len(data.get('results', []))}")
    
    print(f"\n=== Detailed API Results ===")
    for i, notif in enumerate(data.get('results', [])):
        print(f"  {i+1}. {notif.get('title', '')}")
        print(f"     Category: {notif.get('category', '')}")
        print(f"     Unread: {notif.get('is_unread', False)}")
        print(f"     ID: {notif.get('id', '')}")
        print(f"     Text: {notif.get('text', '')}")
        print()
    
    # Calculate what the count SHOULD be
    expected_unread_chat = unread_chat.count()
    expected_unread_tickets = open_tickets.count() + in_progress_tickets.count()
    expected_total = expected_unread_chat + expected_unread_tickets
    
    print(f"=== Count Analysis ===")
    print(f"Expected unread chat: {expected_unread_chat}")
    print(f"Expected unread tickets: {expected_unread_tickets}")
    print(f"Expected total count: {expected_total}")
    print(f"Actual API count: {data.get('unread_count', 0)}")
    print(f"Match: {'✅' if expected_total == data.get('unread_count', 0) else '❌'}")
    
    # Check if there are any old/stale notifications
    print(f"\n=== Stale Notification Check ===")
    
    # Check for very old chat messages that might be causing issues
    old_chat = ChatMessage.objects.filter(recipient=user, is_read=False).order_by('created_at')
    if old_chat.exists():
        print(f"Unread chat messages by date:")
        for msg in old_chat:
            print(f"  - {msg.created_at.strftime('%Y-%m-%d %H:%M')}: {msg.text[:30]}... from {msg.sender.username}")
    
    # Check for any tickets that might be stuck
    stuck_tickets = Ticket.objects.filter(assigned_to=user, status__in=['Open', 'In Progress'])
    if stuck_tickets.exists():
        print(f"\nTickets that might need attention:")
        for ticket in stuck_tickets:
            print(f"  - #{ticket.ticket_id}: {ticket.title} - Status: {ticket.status} - Updated: {ticket.updated_at.strftime('%Y-%m-%d %H:%M')}")
    
    # Check if there's a caching issue by simulating multiple calls
    print(f"\n=== Multiple API Calls Test ===")
    for i in range(3):
        response = agent_notifications_api(request)
        data = json.loads(response.content.decode())
        print(f"Call {i+1}: unread_count = {data.get('unread_count', 0)}")
    
    print(f"\n=== JavaScript Debugging Info ===")
    print("If the count is still showing 4 in the UI, check:")
    print("1. Browser console for JavaScript errors")
    print("2. Network tab for failed API calls")
    print("3. Browser cache (try hard refresh: Ctrl+F5)")
    print("4. JavaScript errors in header.js")
    print("5. CSS issues hiding the badge update")

if __name__ == '__main__':
    debug_notification_count_issue()
