#!/usr/bin/env python
"""
Debug notification badge issue
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.contrib.auth.models import User
from django.test import RequestFactory, Client
from dashboards.views import agent_notifications_api
from tickets.models import ChatMessage, Ticket

def debug_notification_badge():
    print("Debugging Notification Badge Issue...")
    
    # Get the test agent user
    user = User.objects.get(username='testagent')
    print(f"Using test agent: {user.username}")
    
    # Test the API response
    print(f"\n=== API Response Test ===")
    request = RequestFactory().get('/dashboard/agent-dashboard/api/notifications/')
    request.user = user
    
    response = agent_notifications_api(request)
    import json
    data = json.loads(response.content.decode())
    
    print(f"API Status: {response.status_code}")
    print(f"API unread_count: {data.get('unread_count', 0)}")
    print(f"API Response: {data}")
    
    # Check what should be displayed in the badge
    unread_count = data.get('unread_count', 0)
    print(f"\n=== Badge Display Logic ===")
    print(f"Badge should show: '{unread_count}'")
    print(f"Badge should be visible: {'Yes' if unread_count > 0 else 'No'}")
    
    # Check if there are any issues with the notification count calculation
    print(f"\n=== Count Verification ===")
    
    # Check unread chat messages
    unread_chat = ChatMessage.objects.filter(recipient=user, is_read=False)
    print(f"Unread chat messages: {unread_chat.count()}")
    
    # Check ticket notifications
    ticket_notifications = Ticket.objects.filter(assigned_to=user, status__in=['Open', 'In Progress'])
    print(f"Ticket notifications (Open/In Progress): {ticket_notifications.count()}")
    
    # Show ticket details
    print(f"\nTicket Details:")
    for ticket in ticket_notifications:
        print(f"  - #{ticket.ticket_id}: {ticket.title[:50]}... - Status: {ticket.status}")
    
    # Check for any old/stale notifications that might be causing issues
    print(f"\n=== Potential Issues Check ===")
    
    # Check for very old chat messages
    old_chat = ChatMessage.objects.filter(recipient=user, is_read=False).order_by('created_at')
    if old_chat.exists():
        oldest = old_chat.first()
        newest = old_chat.last()
        print(f"Oldest unread chat: {oldest.created_at} - {oldest.text[:30]}...")
        print(f"Newest unread chat: {newest.created_at} - {newest.text[:30]}...")
        print(f"Time span: {(newest.created_at - oldest.created_at).days} days")
    
    # Check for old tickets
    old_tickets = Ticket.objects.filter(assigned_to=user, status__in=['Open', 'In Progress']).order_by('updated_at')
    if old_tickets.exists():
        oldest_ticket = old_tickets.first()
        newest_ticket = old_tickets.last()
        print(f"Oldest active ticket: {oldest_ticket.ticket_id} - Updated: {oldest_ticket.updated_at}")
        print(f"Newest active ticket: {newest_ticket.ticket_id} - Updated: {newest_ticket.updated_at}")
        print(f"Time span: {(newest_ticket.updated_at - oldest_ticket.updated_at).days} days")
    
    print(f"\n=== Browser Debugging Steps ===")
    print("If the badge is still showing '4', try these steps:")
    print("1. Open browser developer tools (F12)")
    print("2. Go to Console tab")
    print("3. Type: document.getElementById('agentNotificationBadge').textContent")
    print("4. Type: document.getElementById('agentNotificationBadge').style.display")
    print("5. Check Network tab for failed API calls")
    print("6. Try hard refresh: Ctrl+F5")
    print("7. Clear browser cache")
    print("8. Check for JavaScript errors in Console")
    
    print(f"\n=== Manual Badge Update Test ===")
    print("In browser console, try:")
    print("1. document.getElementById('agentNotificationBadge').textContent = '0'")
    print("2. document.getElementById('agentNotificationBadge').style.display = 'none'")
    print("3. document.getElementById('agentNotificationBadge').textContent = '1'")
    print("4. document.getElementById('agentNotificationBadge').style.display = 'inline-block'")
    
    print(f"\n=== Expected vs Actual ===")
    print(f"Expected badge count: {unread_count}")
    print(f"If showing '4', there might be:")
    print("  - JavaScript caching issue")
    print("  - Browser cache issue")
    print("  - JavaScript error preventing update")
    print("  - Multiple notification elements")

if __name__ == '__main__':
    debug_notification_badge()
