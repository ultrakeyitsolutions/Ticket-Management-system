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

agent = User.objects.filter(is_staff=True).first()
now = timezone.now()

print('=== Current SLA At Risk Tickets ===')
sla_tickets = Ticket.objects.filter(
    assigned_to=agent,
    status__in=['Open', 'In Progress'],
    priority__in=['High', 'Critical']
).order_by('-created_at')[:5]

print(f'Found {sla_tickets.count()} SLA at-risk tickets:')
for ticket in sla_tickets:
    hours_since = (now - ticket.created_at).total_seconds() / 3600
    print(f'  {ticket.ticket_id}: {ticket.title} ({ticket.priority}) - {hours_since:.1f}h ago')

print(f'\nAgent SLA count: {sla_tickets.count()}')
print('Template should now display these tickets properly.')
