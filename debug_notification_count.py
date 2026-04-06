#!/usr/bin/env python
"""
Debug notification count issue
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

def debug_notification_count():
    print("Debugging Notification Count Issue...")
    
    # Get the test agent user
    user = User.objects.get(username='testagent')
    print(f"Using test agent: {user.username}")
    
    # Check unread chat messages
    unread_chat = ChatMessage.objects.filter(recipient=user, is_read=False)
    print(f"\nUnread chat messages: {unread_chat.count()}")
    
    # Check ticket notifications (based on status)
    ticket_notifications = Ticket.objects.filter(assigned_to=user, status__in=['Open', 'In Progress'])
    print(f"Ticket notifications (Open/In Progress): {ticket_notifications.count()}")
    
    # Show details
    print(f"\nTicket details:")
    for ticket in ticket_notifications:
        print(f"  Ticket #{ticket.ticket_id}: {ticket.title} - Status: {ticket.status}")
    
    print(f"\nUnread chat details:")
    for msg in unread_chat:
        print(f"  From {msg.sender.username}: {msg.text[:50]}...")
    
    # Test the API response
    print(f"\nTesting API response...")
    request = RequestFactory().get('/dashboard/agent-dashboard/api/notifications/')
    request.user = user
    
    response = agent_notifications_api(request)
    import json
    data = json.loads(response.content.decode())
    
    print(f"API unread_count: {data.get('unread_count', 0)}")
    print(f"API results count: {len(data.get('results', []))}")
    
    print(f"\nNotification details from API:")
    for i, notif in enumerate(data.get('results', [])):
        print(f"  {i+1}. {notif.get('title', '')}: unread={notif.get('is_unread', False)}")
    
    # Calculate expected count
    expected_count = unread_chat.count() + ticket_notifications.count()
    print(f"\nExpected unread count: {expected_count}")
    print(f"Actual API count: {data.get('unread_count', 0)}")
    print(f"Match: {'✅' if expected_count == data.get('unread_count', 0) else '❌'}")

if __name__ == '__main__':
    debug_notification_count()
