#!/usr/bin/env python
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from apps.core.models import Ticket

# Get all unique statuses
statuses = Ticket.objects.values_list('status', flat=True).distinct()
print("All ticket statuses in database:")
for status in statuses:
    count = Ticket.objects.filter(status=status).count()
    print(f"  {status}: {count} tickets")

# Check today's tickets
from django.utils import timezone
today = timezone.now().date()
print(f"\nTickets updated today ({today}):")

for status in statuses:
    count = Ticket.objects.filter(status=status, updated_at__date=today).count()
    if count > 0:
        print(f"  {status}: {count} tickets")

# Check agent users
agent_users = User.objects.filter(is_staff=True)
print(f"\nAgent users:")
for agent in agent_users:
    print(f"  {agent.username} (ID: {agent.id})")
    
    # Check tickets assigned to this agent
    assigned = Ticket.objects.filter(assigned_to=agent)
    print(f"    Total assigned: {assigned.count()}")
    
    # Check resolved/closed today
    resolved_today = assigned.filter(status__in=['Resolved', 'Closed'], updated_at__date=today).count()
    print(f"    Resolved/Closed today: {resolved_today}")
    
    # Show recent tickets
    recent = assigned.filter(updated_at__date=today).values('ticket_id', 'status', 'updated_at')
    for ticket in recent:
        print(f"      Ticket {ticket['ticket_id']}: {ticket['status']} at {ticket['updated_at']}")
