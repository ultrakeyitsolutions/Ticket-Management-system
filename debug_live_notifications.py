#!/usr/bin/env python
"""
Debug live notification issues
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

def debug_live_notifications():
    print("Debugging Live Notification Issues...")
    
    # Get the test agent user
    user = User.objects.get(username='testagent')
    print(f"Using test agent: {user.username}")
    
    # Check current state
    print(f"\n=== Current Notification State ===")
    
    # Check unread chat messages
    unread_chat = ChatMessage.objects.filter(recipient=user, is_read=False)
    print(f"Unread chat messages: {unread_chat.count()}")
    for msg in unread_chat:
        print(f"  - Chat {msg.id}: {msg.text[:50]}... from {msg.sender.username}")
    
    # Check ticket notifications (Open/In Progress)
    ticket_notifications = Ticket.objects.filter(assigned_to=user, status__in=['Open', 'In Progress'])
    print(f"\nTicket notifications (Open/In Progress): {ticket_notifications.count()}")
    for ticket in ticket_notifications:
        print(f"  - Ticket #{ticket.ticket_id}: {ticket.title} - Status: {ticket.status}")
    
    # Test the API response
    print(f"\n=== API Response ===")
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
        print(f"     Text: {notif.get('text', '')[:50]}...")
        print()
    
    # Calculate expected count
    expected_count = unread_chat.count() + ticket_notifications.count()
    print(f"=== Summary ===")
    print(f"Expected unread count: {expected_count}")
    print(f"Actual API count: {data.get('unread_count', 0)}")
    print(f"Match: {'✅' if expected_count == data.get('unread_count', 0) else '❌'}")
    
    if expected_count != data.get('unread_count', 0):
        print(f"\n⚠️  COUNT MISMATCH DETECTED!")
        print(f"This suggests there might be an issue with the notification calculation.")
    
    # Check if there are any issues with the notification logic
    print(f"\n=== Debugging Notification Logic ===")
    
    # Simulate the notification building process
    notifications = []
    
    # Ticket notifications
    ticket_qs = Ticket.objects.select_related('created_by').filter(assigned_to=user).order_by('-updated_at')[:20]
    for t in ticket_qs:
        notifications.append({
            'id': f"ticket_{t.ticket_id}",
            'category': 'tickets',
            'timestamp': t.updated_at,
            'is_unread': t.status in ['Open', 'In Progress'],
            'title': 'Assigned ticket',
            'text': f"Ticket #{t.ticket_id} · {t.title} · status: {t.status}",
        })
    
    # Chat notifications
    chat_qs = ChatMessage.objects.select_related('sender').filter(recipient=user).order_by('-created_at')[:20]
    for m in chat_qs:
        notifications.append({
            'id': f"chat_{m.id}",
            'category': 'system',
            'timestamp': m.created_at,
            'is_unread': not m.is_read,
            'title': 'New message',
            'text': f"New message from {m.sender.get_full_name() or m.sender.username}",
        })
    
    notifications.sort(key=lambda n: n['timestamp'], reverse=True)
    top = notifications[:5]
    debug_unread_count = sum(1 for n in notifications if n.get('is_unread'))
    
    print(f"Debug unread count (all notifications): {debug_unread_count}")
    print(f"Debug unread count (top 5): {sum(1 for n in top if n.get('is_unread'))}")
    
    print(f"\n=== Recommendations ===")
    if unread_chat.count() > 0:
        print("📝 There are unread chat messages. Users should be able to:")
        print("   - Click on individual chat notifications to mark them as read")
        print("   - Use 'Mark all as read' to mark all chat messages as read")
    
    if ticket_notifications.count() > 0:
        print("🎫 There are ticket notifications (Open/In Progress). These will remain 'unread' until:")
        print("   - Ticket status changes to 'Resolved', 'Closed', etc.")
        print("   - This is correct behavior - ticket status represents actual work state")

if __name__ == '__main__':
    debug_live_notifications()
