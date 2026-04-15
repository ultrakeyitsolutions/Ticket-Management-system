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

print("=== Check Exact Ticket IDs ===")

agent = User.objects.filter(is_staff=True).first()

# Check all tickets assigned to agent
all_tickets = Ticket.objects.filter(assigned_to=agent).order_by('-created_at')
print(f"All tickets assigned to {agent.username}: {all_tickets.count()}")

for ticket in all_tickets:
    print(f"\n{ticket.ticket_id}:")
    print(f"  Priority: {ticket.priority}")
    print(f"  Status: {ticket.status}")
    print(f"  Created: {ticket.created_at}")
    
    # Calculate due date
    sla_hours = {
        'Critical': 1,
        'High': 2,
        'Medium': 8,
        'Low': 24,
    }
    
    if ticket.status not in ['Resolved', 'Closed']:
        hours = sla_hours.get(ticket.priority, 24)
        due_date = ticket.created_at + timezone.timedelta(hours=hours)
        is_overdue = due_date < timezone.now()
        
        print(f"  Due Date: {due_date}")
        print(f"  Is Overdue: {'YES' if is_overdue else 'NO'}")
        print(f"  Template should show: {due_date.strftime('%M %d %H:%M') if not is_overdue else 'OVERDUE - ' + due_date.strftime('%M %d %H:%M')}")
    else:
        print(f"  Due Date: None (resolved)")
        print(f"  Template should show: -")
