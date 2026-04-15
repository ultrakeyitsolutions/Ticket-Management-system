#!/usr/bin/env python
import os
import sys

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django manually
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.contrib.auth.models import User
from tickets.models import Ticket

def check_channel_data():
    print("=== CHECKING CHANNEL DATA ===\n")
    
    # Check all tickets
    all_tickets = Ticket.objects.all()
    total_count = all_tickets.count()
    print(f"Total tickets in database: {total_count}")
    
    # Check channel distribution
    print(f"\n=== CHANNEL DISTRIBUTION ===")
    channels = ['Email', 'Phone', 'Chat', 'Web']
    
    for channel in channels:
        count = Ticket.objects.filter(channel=channel).count()
        print(f"{channel}: {count}")
    
    # Check tickets with null channel
    null_count = Ticket.objects.filter(channel__isnull=True).count()
    print(f"Null channel: {null_count}")
    
    # Check specific agent tickets
    agent_user = User.objects.filter(username='sathvika.arikatla').first()
    if agent_user:
        agent_tickets = Ticket.objects.filter(assigned_to=agent_user)
        print(f"\n=== AGENT TICKETS (sathvika.arikatla) ===")
        print(f"Total: {agent_tickets.count()}")
        
        for ticket in agent_tickets:
            print(f"{ticket.ticket_id}: {ticket.title} - Channel: {ticket.channel or 'NULL'}")
    
    # Check some sample tickets
    print(f"\n=== SAMPLE TICKETS ===")
    for ticket in Ticket.objects.all()[:10]:
        print(f"{ticket.ticket_id}: Channel = '{ticket.channel or 'NULL'}'")

if __name__ == '__main__':
    check_channel_data()
