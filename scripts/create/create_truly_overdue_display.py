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

print("=== Create Truly Overdue Ticket ===")

agent = User.objects.filter(is_staff=True).first()
now = timezone.now()

# Create a ticket 10 hours ago (definitely overdue for Critical 1hr SLA)
overdue_time = now - timezone.timedelta(hours=10)

overdue_ticket = Ticket.objects.create(
    ticket_id='TRULY-OVERDUE-DISPLAY',
    title='Truly Overdue Ticket',
    description='This ticket is 10 hours old - should definitely show RED',
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
time_diff = now - due_date
hours_overdue = time_diff.total_seconds() / 3600

print(f"  Due Date: {due_date}")
print(f"  Hours Overdue: {hours_overdue:.1f}")
print(f"  Is Overdue: {'YES - should show RED' if hours_overdue > 0 else 'NO'}")

# Also create a normal on-time ticket for comparison
normal_time = now - timezone.timedelta(minutes=30)
normal_ticket = Ticket.objects.create(
    ticket_id='NORMAL-TIME-DISPLAY',
    title='Normal Time Ticket',
    description='This ticket is within SLA',
    priority='Critical',
    status='Open',
    assigned_to=agent,
    created_by=agent,
    created_at=normal_time,
    updated_at=normal_time
)

normal_due = normal_ticket.created_at + timezone.timedelta(hours=1)
print(f"\nCreated normal ticket: {normal_ticket.ticket_id}")
print(f"  Due Date: {normal_due}")
print(f"  Should show: Normal due date (not red)")

print(f"\n✅ Test tickets created!")
print(f"Visit: http://127.0.0.1:8000/dashboard/agent-dashboard/agenttickets.html")
print(f"You should see:")
print(f"  - '{overdue_ticket.ticket_id}' with RED due date")
print(f"  - '{normal_ticket.ticket_id}' with normal due date")
