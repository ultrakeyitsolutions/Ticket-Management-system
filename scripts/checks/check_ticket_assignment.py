#!/usr/bin/env python
import os
import sys

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from tickets.models import Ticket, UserRating
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Q, Count

print("=== Ticket Assignment Analysis ===")

# Check all tickets
all_tickets = Ticket.objects.all()
print(f"Total tickets: {all_tickets.count()}")

if all_tickets.count() > 0:
    print("\n--- Sample Tickets ---")
    for ticket in all_tickets[:10]:
        assigned_to_name = ticket.assigned_to.username if ticket.assigned_to else "None"
        created_by_name = ticket.created_by.username if ticket.created_by else "None"
        print(f"Ticket {ticket.ticket_id}: status='{ticket.status}', assigned_to={assigned_to_name}, created_by={created_by_name}")
    
    # Check tickets by status
    print("\n--- Tickets by Status ---")
    statuses = Ticket.objects.values('status').annotate(count=Count('status'))
    for status_info in statuses:
        print(f"{status_info['status']}: {status_info['count']} tickets")
    
    # Check unassigned tickets
    unassigned = Ticket.objects.filter(assigned_to__isnull=True)
    print(f"\nUnassigned tickets: {unassigned.count()}")
    
    # Check today's tickets
    today = timezone.now().date()
    today_tickets = Ticket.objects.filter(updated_at__date=today)
    print(f"Tickets updated today: {today_tickets.count()}")
    
    if today_tickets.count() > 0:
        print("\n--- Today's Tickets ---")
        for ticket in today_tickets:
            assigned_to_name = ticket.assigned_to.username if ticket.assigned_to else "None"
            print(f"Ticket {ticket.ticket_id}: status='{ticket.status}', assigned_to={assigned_to_name}")
    
    # Check if there are any resolved/closed tickets at all
    resolved_tickets = Ticket.objects.filter(status__in=['Resolved', 'Closed'])
    print(f"\nTotal resolved/closed tickets: {resolved_tickets.count()}")
    
    if resolved_tickets.count() > 0:
        print("\n--- Recent Resolved/Closed Tickets ---")
        for ticket in resolved_tickets[:5]:
            assigned_to_name = ticket.assigned_to.username if ticket.assigned_to else "None"
            print(f"Ticket {ticket.ticket_id}: status='{ticket.status}', assigned_to={assigned_to_name}, updated_at={ticket.updated_at}")

else:
    print("No tickets found in database!")

print("\n=== Recommendation ===")
print("The issue is that tickets are not being assigned to agents.")
print("To test the performance dashboard, you need to:")
print("1. Create some test tickets")
print("2. Assign them to agents")
print("3. Update their status to 'Resolved' or 'Closed'")
print("4. The resolved_today count will then show the correct number")
