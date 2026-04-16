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
from django.db.models import Q

print("=== Creating Test Performance Data ===")

# Get an agent user
agent = User.objects.filter(is_staff=True).first()
if not agent:
    print("No agent user found!")
    sys.exit(1)

print(f"Using agent: {agent.username} (ID: {agent.id})")

# Get some unassigned tickets
unassigned_tickets = Ticket.objects.filter(assigned_to__isnull=True)[:5]
print(f"Found {unassigned_tickets.count()} unassigned tickets")

today = timezone.now()

# Assign and resolve some tickets today
for i, ticket in enumerate(unassigned_tickets):
    ticket.assigned_to = agent
    ticket.status = 'Resolved'
    # Use save() with update_fields to ensure updated_at is set to today
    ticket.save()
    print(f"Assigned and resolved ticket {ticket.ticket_id} to {agent.username}")
    
    # Verify the save worked
    ticket.refresh_from_db()
    print(f"  Verification - Updated at: {ticket.updated_at.date()}, Status: {ticket.status}")

# Also update one existing assigned ticket to be resolved today
assigned_tickets = Ticket.objects.filter(assigned_to=agent, status='Open').first()
if assigned_tickets:
    assigned_tickets.status = 'Resolved'
    assigned_tickets.updated_at = today
    assigned_tickets.save()
    print(f"Updated existing ticket {assigned_tickets.ticket_id} to Resolved")

# Check the results
resolved_today = Ticket.objects.filter(
    assigned_to=agent,
    status='Resolved',
    updated_at__date=today.date()
).count()

print(f"\n=== Result ===")
print(f"Agent {agent.username} has resolved {resolved_today} tickets today!")
print(f"Visit http://127.0.0.1:8000/dashboard/agent-dashboard/ to see the updated performance")
