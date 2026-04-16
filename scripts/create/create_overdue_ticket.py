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

print("=== Create Overdue Ticket ===")

agent = User.objects.filter(is_staff=True).first()
now = timezone.now()

# Create an overdue Critical ticket (created 2 hours ago, SLA is 1 hour)
overdue_time = now - timezone.timedelta(hours=2)

overdue_ticket = Ticket.objects.create(
    ticket_id='OVERDUE-CRITICAL-001',
    title='Overdue Critical Ticket',
    description='This critical ticket is overdue - should show red due date',
    priority='Critical',
    status='Open',
    assigned_to=agent,
    created_by=agent,
    created_at=overdue_time,
    updated_at=overdue_time
)

print(f"Created overdue ticket: {overdue_ticket.ticket_id}")
print(f"  Priority: {overdue_ticket.priority}")
print(f"  Status: {overdue_ticket.status}")
print(f"  Created: {overdue_ticket.created_at}")
print(f"  Current time: {now}")

# Calculate due date
sla_hours = {'Critical': 1, 'High': 2, 'Medium': 8, 'Low': 24}
due_date = overdue_ticket.created_at + timezone.timedelta(hours=sla_hours['Critical'])
is_overdue = due_date < now

print(f"  Due Date: {due_date}")
print(f"  Is Overdue: {'YES' if is_overdue else 'NO'}")

print(f"\n✅ Overdue ticket created!")
print(f"This ticket should show a RED due date on the agent tickets page")
