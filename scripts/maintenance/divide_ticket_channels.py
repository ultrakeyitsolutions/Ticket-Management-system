#!/usr/bin/env python
import os
import sys

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django manually
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from tickets.models import Ticket

def divide_ticket_channels():
    print("=== DIVIDING TICKETS ACROSS CHANNELS ===\n")
    
    # Get all tickets
    all_tickets = Ticket.objects.all()
    total_count = all_tickets.count()
    
    print(f"Total tickets to distribute: {total_count}")
    
    # Distribute tickets across channels
    channels = ['Email', 'Phone', 'Chat', 'Web']
    
    updated_count = 0
    for i, ticket in enumerate(all_tickets):
        # Distribute evenly across channels
        channel_index = i % len(channels)
        ticket.channel = channels[channel_index]
        ticket.save(update_fields=['channel'])
        updated_count += 1
        
        if updated_count <= 20:  # Show first 20 updates
            print(f"Updated {ticket.ticket_id}: {ticket.channel}")
    
    print(f"\nUpdated {updated_count} tickets with diverse channel data")
    
    # Show new distribution
    print(f"\n=== NEW CHANNEL DISTRIBUTION ===")
    for channel in channels:
        count = Ticket.objects.filter(channel=channel).count()
        print(f"{channel}: {count}")

if __name__ == '__main__':
    divide_ticket_channels()
