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
from django.db.models import Q, F, DurationField, ExpressionWrapper

print("=== Fix SLA Calculation ===")

agent = User.objects.filter(is_staff=True).first()
now = timezone.now()

print(f"Agent: {agent.username}")
print(f"Current time: {now}")

# Delete the test tickets and create proper ones
Ticket.objects.filter(ticket_id__startswith='SLA-').delete()

# Create tickets with proper timestamps
test_tickets = [
    {
        'ticket_id': 'SLA-CRITICAL-001',
        'priority': 'Critical',
        'status': 'Open',
        'hours_ago': 2  # 2 hours ago (Critical SLA is 1 hour)
    },
    {
        'ticket_id': 'SLA-HIGH-001', 
        'priority': 'High',
        'status': 'In Progress',
        'hours_ago': 3  # 3 hours ago (High SLA is 2 hours)
    },
    {
        'ticket_id': 'SLA-HIGH-002',
        'priority': 'High', 
        'status': 'Open',
        'hours_ago': 0.5  # 30 minutes ago (within SLA)
    }
]

for ticket_data in test_tickets:
    created_time = now - timezone.timedelta(hours=ticket_data['hours_ago'])
    
    ticket = Ticket.objects.create(
        ticket_id=ticket_data['ticket_id'],
        title=f"{'Critical' if ticket_data['priority'] == 'Critical' else 'High'} Priority Issue",
        description=f"Test ticket for SLA calculation",
        priority=ticket_data['priority'],
        status=ticket_data['status'],
        assigned_to=agent,
        created_by=agent,
        created_at=created_time,
        updated_at=created_time
    )
    
    print(f"Created: {ticket.ticket_id}")
    print(f"  Priority: {ticket.priority}, Status: {ticket.status}")
    print(f"  Created: {ticket.created_at}")
    print(f"  Hours ago: {ticket_data['hours_ago']}")

print(f"\n=== Test Different SLA Calculations ===")

# Current calculation (priority-based only)
current_sla = Ticket.objects.filter(
    assigned_to=agent,
    status__in=['Open', 'In Progress'],
    priority__in=['High', 'Critical']
).count()

print(f"1. Current SLA (priority only): {current_sla}")

# Improved calculation (time-based SLA)
sla_at_risk_time = 0
for ticket in Ticket.objects.filter(assigned_to=agent, status__in=['Open', 'In Progress']):
    time_since_creation = now - ticket.created_at
    hours_since = time_since_creation.total_seconds() / 3600
    
    sla_breach = False
    if ticket.priority == 'Critical' and hours_since > 1:
        sla_breach = True
    elif ticket.priority == 'High' and hours_since > 2:
        sla_breach = True
    elif ticket.priority == 'Medium' and hours_since > 8:
        sla_breach = True
    elif ticket.priority == 'Low' and hours_since > 24:
        sla_breach = True
    
    if sla_breach:
        sla_at_risk_time += 1
        print(f"  SLA BREACH: {ticket.ticket_id} - {ticket.priority} for {hours_since:.1f} hours")

print(f"2. Time-based SLA At Risk: {sla_at_risk_time}")

# Database query version (more efficient)
sla_at_risk_query = Ticket.objects.filter(
    assigned_to=agent,
    status__in=['Open', 'In Progress']
).filter(
    Q(priority='Critical', created_at__lt=now - timezone.timedelta(hours=1)) |
    Q(priority='High', created_at__lt=now - timezone.timedelta(hours=2)) |
    Q(priority='Medium', created_at__lt=now - timezone.timedelta(hours=8)) |
    Q(priority='Low', created_at__lt=now - timezone.timedelta(hours=24))
).count()

print(f"3. Database query SLA At Risk: {sla_at_risk_query}")

print(f"\n=== Recommendation ===")
print(f"Use the time-based SLA calculation for accurate risk assessment!")
