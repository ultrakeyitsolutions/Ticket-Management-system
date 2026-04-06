#!/usr/bin/env python
import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from tickets.models import Ticket

def check_ticket_priority_data():
    print("=== Ticket Priority Data Check ===")
    
    # Check total tickets
    total_tickets = Ticket.objects.count()
    print(f"Total tickets: {total_tickets}")
    
    # Check tickets by priority
    priorities = ['Low', 'Medium', 'High', 'Critical']
    print("\nTickets by priority:")
    for priority in priorities:
        count = Ticket.objects.filter(priority=priority).count()
        print(f"  {priority}: {count}")
    
    # Check sample tickets with their priorities
    print("\nSample tickets (first 10):")
    tickets = Ticket.objects.all()[:10]
    for ticket in tickets:
        print(f"  {ticket.ticket_id}: {ticket.title[:30]}... (Priority: {ticket.priority})")
    
    # Check if there are any tickets assigned to agents
    print(f"\nTickets assigned to agents: {Ticket.objects.filter(assigned_to__isnull=False).count()}")

if __name__ == "__main__":
    check_ticket_priority_data()
