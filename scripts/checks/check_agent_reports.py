#!/usr/bin/env python
import os
import sys

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django manually
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.contrib.auth.models import User
from tickets.models import Ticket

def check_agent_tickets():
    print("=== CHECK AGENT TICKETS AND STATUS ===\n")
    
    # Find agent users
    agent_users = User.objects.filter(
        userprofile__role__name__iexact='agent'
    ).distinct()
    
    if not agent_users.exists():
        print("No agent users found!")
        # Try staff users as fallback
        agent_users = User.objects.filter(is_staff=True)
        if not agent_users.exists():
            print("No staff users found either!")
            return
    
    for agent in agent_users:
        print(f"\n=== AGENT: {agent.username} ===")
        
        # Get assigned tickets
        assigned_tickets = Ticket.objects.filter(assigned_to=agent)
        total_count = assigned_tickets.count()
        
        print(f"Total assigned tickets: {total_count}")
        
        if total_count == 0:
            print("No tickets assigned to this agent")
            continue
        
        # Count by status
        status_counts = {}
        for status in ['Open', 'In Progress', 'Resolved', 'Closed']:
            count = assigned_tickets.filter(status=status).count()
            status_counts[status] = count
            print(f"{status}: {count}")
        
        # Calculate percentages
        print("\nPercentages:")
        for status, count in status_counts.items():
            if total_count > 0:
                pct = round((count / total_count) * 100, 1)
                print(f"{status}: {pct}%")
        
        # Show some sample tickets
        print("\nSample tickets:")
        for ticket in assigned_tickets[:5]:
            print(f"  {ticket.ticket_id}: {ticket.title} - {ticket.status}")

if __name__ == '__main__':
    check_agent_tickets()
