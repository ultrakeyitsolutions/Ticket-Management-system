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

print("=== Create SLA Test Tickets ===")

agent = User.objects.filter(is_staff=True).first()
now = timezone.now()

print(f"Agent: {agent.username}")
print(f"Current time: {now}")

# Create tickets that should be SLA At Risk
test_tickets = [
    {
        'ticket_id': 'SLA-CRITICAL-001',
        'title': 'Critical System Down',
        'priority': 'Critical',
        'status': 'Open',
        'description': 'Critical ticket created 2 hours ago - should be SLA breach'
    },
    {
        'ticket_id': 'SLA-HIGH-001', 
        'title': 'High Priority Issue',
        'priority': 'High',
        'status': 'In Progress',
        'description': 'High priority ticket created 3 hours ago - should be SLA breach'
    },
    {
        'ticket_id': 'SLA-HIGH-002',
        'title': 'Another High Issue', 
        'priority': 'High',
        'status': 'Open',
        'description': 'High priority ticket created 30 minutes ago - should NOT be SLA breach yet'
    }
]

for ticket_data in test_tickets:
    # Create ticket with appropriate timestamp
    if ticket_data['ticket_id'] == 'SLA-CRITICAL-001':
        # Created 2 hours ago (Critical SLA is 1 hour)
        created_time = now - timezone.timedelta(hours=2)
    elif ticket_data['ticket_id'] == 'SLA-HIGH-001':
        # Created 3 hours ago (High SLA is 2 hours)
        created_time = now - timezone.timedelta(hours=3)
    else:
        # Created 30 minutes ago (within SLA)
        created_time = now - timezone.timedelta(minutes=30)
    
    ticket = Ticket.objects.create(
        ticket_id=ticket_data['ticket_id'],
        title=ticket_data['title'],
        description=ticket_data['description'],
        priority=ticket_data['priority'],
        status=ticket_data['status'],
        assigned_to=agent,
        created_by=agent,
        created_at=created_time,
        updated_at=created_time
    )
    
    print(f"Created: {ticket.ticket_id}")
    print(f"  Priority: {ticket.priority}")
    print(f"  Status: {ticket.status}")
    print(f"  Created: {ticket.created_at}")
    print(f"  Hours since creation: {(now - ticket.created_at).total_seconds() / 3600:.1f}")

print(f"\n=== Test Current SLA Calculation ===")

# Test current SLA calculation
sla_at_risk_current = Ticket.objects.filter(
    assigned_to=agent,
    status__in=['Open', 'In Progress'],
    priority__in=['High', 'Critical']
).count()

print(f"Current SLA At Risk (priority-based only): {sla_at_risk_current}")

# Show which tickets match
current_sla_tickets = Ticket.objects.filter(
    assigned_to=agent,
    status__in=['Open', 'In Progress'],
    priority__in=['High', 'Critical']
)

print(f"Tickets matching current SLA calculation:")
for ticket in current_sla_tickets:
    hours_since = (now - ticket.created_at).total_seconds() / 3600
    print(f"  {ticket.ticket_id}: {ticket.priority} for {hours_since:.1f} hours - {'BREACH' if (ticket.priority == 'Critical' and hours_since > 1) or (ticket.priority == 'High' and hours_since > 2) else 'OK'}")
