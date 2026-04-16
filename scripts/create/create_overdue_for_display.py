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

print("=== Create Overdue Ticket for Display Test ===")

agent = User.objects.filter(is_staff=True).first()
now = timezone.now()

# Create a ticket that's definitely overdue (created 5 hours ago, Critical SLA is 1 hour)
overdue_time = now - timezone.timedelta(hours=5)

overdue_ticket = Ticket.objects.create(
    ticket_id='DISPLAY-OVERDUE-001',
    title='Overdue Ticket for Display Test',
    description='This ticket is 5 hours old, should show RED due date',
    priority='Critical',
    status='Open',
    assigned_to=agent,
    created_by=agent,
    created_at=overdue_time,
    updated_at=overdue_time
)

print(f"Created overdue ticket: {overdue_ticket.ticket_id}")
print(f"  Created: {overdue_ticket.created_at}")
print(f"  Current time: {now}")

# Calculate due date (1 hour for Critical)
due_date = overdue_ticket.created_at + timezone.timedelta(hours=1)
is_overdue = due_date < now

print(f"  Due Date: {due_date}")
print(f"  Is Overdue: {'YES - should show RED' if is_overdue else 'NO'}")

print(f"\n✅ Test ticket created!")
print(f"Visit: http://127.0.0.1:8000/dashboard/agent-dashboard/agenttickets.html")
print(f"You should see '{overdue_ticket.ticket_id}' with RED due date in the Due column")
