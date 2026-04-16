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

print("=== Check Open Tickets ===")

agent = User.objects.filter(is_staff=True).first()

# Look for our test tickets specifically
test_tickets = Ticket.objects.filter(
    assigned_to=agent,
    ticket_id__startswith=['DUE-TEST', 'OVERDUE', 'TRULY-OVERDUE', 'NORMAL-TIME']
).order_by('-created_at')

print(f"Found {test_tickets.count()} test tickets:")

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

for ticket in test_tickets:
    due_date = calculate_due_date(ticket)
    
    print(f"\n{ticket.ticket_id}:")
    print(f"  Priority: {ticket.priority}")
    print(f"  Status: {ticket.status}")
    print(f"  Created: {ticket.created_at}")
    print(f"  Due Date: {due_date}")
    
    if due_date:
        now = timezone.now()
        is_overdue = due_date < now
        print(f"  Is Overdue: {'YES' if is_overdue else 'NO'}")
        print(f"  Should show in template: {due_date.strftime('%M %d %H:%M')}")
    else:
        print(f"  Should show in template: -")

# Also check what the agenttickets view would return
print(f"\n=== Simulating Agent Tickets View ===")

# Simulate what the view does
base_qs = Ticket.objects.select_related('created_by').filter(assigned_to=agent)
open_tickets = base_qs.filter(status='Open')
pending_tickets = base_qs.filter(status='In Progress')

print(f"Open tickets: {open_tickets.count()}")
print(f"In Progress tickets: {pending_tickets.count()}")

for ticket in open_tickets:
    print(f"  Open: {ticket.ticket_id} - {ticket.priority}")

for ticket in pending_tickets:
    print(f"  In Progress: {ticket.ticket_id} - {ticket.priority}")
