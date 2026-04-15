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
import datetime as dt

print("=== Create Truly Overdue Ticket ===")

agent = User.objects.filter(is_staff=True).first()
now = timezone.now()

# Create a ticket 3 hours ago (for Critical, SLA is 1 hour, so this should be overdue)
overdue_time = now - timezone.timedelta(hours=3)

overdue_ticket = Ticket.objects.create(
    ticket_id='TRULY-OVERDUE-001',
    title='Truly Overdue Critical Ticket',
    description='This critical ticket is definitely overdue - should show red due date',
    priority='Critical',
    status='Open',
    assigned_to=agent,
    created_by=agent,
    created_at=overdue_time,
    updated_at=overdue_time
)

print(f"Created truly overdue ticket: {overdue_ticket.ticket_id}")
print(f"  Created: {overdue_ticket.created_at}")
print(f"  Current time: {now}")

# Calculate due date (1 hour for Critical)
due_date = overdue_ticket.created_at + timezone.timedelta(hours=1)
is_overdue = due_date < now

print(f"  Due Date: {due_date}")
print(f"  Is Overdue: {'YES' if is_overdue else 'NO'}")

# Also create a normal on-time ticket for comparison
normal_time = now - timezone.timedelta(minutes=30)
normal_ticket = Ticket.objects.create(
    ticket_id='NORMAL-TIME-001',
    title='Normal Time Critical Ticket',
    description='This critical ticket is within SLA',
    priority='Critical',
    status='Open',
    assigned_to=agent,
    created_by=agent,
    created_at=normal_time,
    updated_at=normal_time
)

normal_due = normal_ticket.created_at + timezone.timedelta(hours=1)
normal_overdue = normal_due < now

print(f"\nCreated normal ticket: {normal_ticket.ticket_id}")
print(f"  Due Date: {normal_due}")
print(f"  Is Overdue: {'YES' if normal_overdue else 'NO'}")

print(f"\n✅ Test tickets created!")
print(f"Visit http://127.0.0.1:8000/dashboard/agent-dashboard/agenttickets.html")
print(f"You should see:")
print(f"  - TRULY-OVERDUE-001 with RED due date")
print(f"  - NORMAL-TIME-001 with normal due date")
