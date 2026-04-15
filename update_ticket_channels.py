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
import random

def update_ticket_channels():
    print("=== UPDATING TICKET CHANNELS ===\n")
    
    # Get all tickets without channel data
    tickets_without_channel = Ticket.objects.filter(channel__isnull=True)
    total_tickets = tickets_without_channel.count()
    
    print(f"Found {total_tickets} tickets without channel data")
    
    if total_tickets == 0:
        print("All tickets already have channel data!")
        return
    
    # Channel choices
    channels = ['Email', 'Phone', 'Chat', 'Web']
    
    # Update tickets with random channel data
    updated_count = 0
    for ticket in tickets_without_channel:
        # Assign random channel
        ticket.channel = random.choice(channels)
        ticket.save(update_fields=['channel'])
        updated_count += 1
        
        if updated_count <= 10:  # Show first 10 updates
            print(f"Updated {ticket.ticket_id}: {ticket.channel}")
    
    print(f"\nUpdated {updated_count} tickets with channel data")
    
    # Show channel distribution
    print(f"\n=== CHANNEL DISTRIBUTION ===")
    for channel in channels:
        count = Ticket.objects.filter(channel=channel).count()
        print(f"{channel}: {count}")
    
    # Update specific test tickets for our agent
    agent_user = User.objects.filter(username='sathvika.arikatla').first()
    if agent_user:
        agent_tickets = Ticket.objects.filter(assigned_to=agent_user)
        print(f"\n=== AGENT TICKETS CHANNEL UPDATE ===")
        for ticket in agent_tickets:
            # Set specific channels for testing
            if 'Login' in ticket.title:
                ticket.channel = 'Email'
            elif 'Payment' in ticket.title:
                ticket.channel = 'Phone'
            elif 'Password' in ticket.title:
                ticket.channel = 'Chat'
            elif 'Feature' in ticket.title:
                ticket.channel = 'Web'
            else:
                ticket.channel = 'Email'
            
            ticket.save(update_fields=['channel'])
            print(f"Updated {ticket.ticket_id}: {ticket.channel}")

if __name__ == '__main__':
    update_ticket_channels()
