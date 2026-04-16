#!/usr/bin/env python
import os
import sys

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from tickets.models import Ticket
from django.contrib.auth.models import User
from django.utils import timezone

print("=== Check Current Open Tickets ===")

agent = User.objects.filter(is_staff=True).first()

# Get all open tickets assigned to agent
open_tickets = Ticket.objects.filter(
    assigned_to=agent,
    status='Open'
).order_by('-created_at')

print(f"Found {open_tickets.count()} open tickets:")

def calculate_due_date(ticket):
    sla_hours = {
        'Critical': 1,
        'High': 2,
        'Medium': 8,
        'Low': 24,
    }
    
    if ticket.status in ['Resolved', 'Closed']:
        return None
    
    hours = sla_hours.get(ticket.priority, 24)
    return ticket.created_at + timezone.timedelta(hours=hours)

for ticket in open_tickets:
    due_date = calculate_due_date(ticket)
    
    print(f"\n{ticket.ticket_id}:")
    print(f"  Title: {ticket.title}")
    print(f"  Priority: {ticket.priority}")
    print(f"  Created: {ticket.created_at}")
    print(f"  Due Date: {due_date}")
    
    if due_date:
        now = timezone.now()
        is_overdue = due_date < now
        print(f"  Is Overdue: {'YES' if is_overdue else 'NO'}")
        print(f"  Should Display: {due_date.strftime('%M %d %H:%M') if not is_overdue else 'RED - ' + due_date.strftime('%M %d %H:%M')}")

print(f"\n=== Summary ===")
print(f"Open tickets should show due dates in the Due column")
print(f"Visit: http://127.0.0.1:8000/dashboard/agent-dashboard/agenttickets.html")
print(f"Check if these tickets show their due dates correctly")
