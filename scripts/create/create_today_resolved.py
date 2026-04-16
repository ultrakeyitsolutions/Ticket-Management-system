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
import datetime

print("=== Create Today Resolved Ticket ===")

agent = User.objects.filter(is_staff=True).first()
today = timezone.now()

print(f"Agent: {agent.username}")
print(f"Current time: {today}")

# Create a new ticket and resolve it today
new_ticket = Ticket.objects.create(
    title="Test Ticket for Today",
    description="This ticket was created and resolved today",
    status='Resolved',
    priority='Medium',
    assigned_to=agent,
    created_by=agent,
    ticket_id=f"TODAY-RESOLVE-{timezone.now().strftime('%H%M%S')}",
    updated_at=today
)

print(f"Created ticket: {new_ticket.ticket_id}")
print(f"  Status: {new_ticket.status}")
print(f"  Updated at: {new_ticket.updated_at}")
print(f"  Updated at date: {new_ticket.updated_at.date()}")

# Test the queries
simple_date_query = Ticket.objects.filter(
    assigned_to=agent,
    status='Resolved',
    updated_at__date=today.date()
).count()

range_query = Ticket.objects.filter(
    assigned_to=agent,
    status='Resolved',
    updated_at__range=(
        timezone.make_aware(datetime.datetime.combine(today.date(), datetime.time.min)),
        timezone.make_aware(datetime.datetime.combine(today.date(), datetime.time.max))
    )
).count()

print(f"\nQuery results:")
print(f"  Simple date query: {simple_date_query}")
print(f"  Range query: {range_query}")

# Check the actual stored value
new_ticket.refresh_from_db()
print(f"\nActual stored values:")
print(f"  Updated at: {new_ticket.updated_at}")
print(f"  Timezone: {new_ticket.updated_at.tzinfo}")
print(f"  Date only: {new_ticket.updated_at.date()}")
