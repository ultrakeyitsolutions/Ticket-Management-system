#!/usr/bin/env python
import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from tickets.models import Ticket
from django.contrib.auth.models import User
from django.db.models import Count

def test_priority_data_directly():
    print("=== Testing Priority Data Directly ===")
    
    # Find an agent user or any user with assigned tickets
    agent_user = None
    for user in User.objects.all():
        if Ticket.objects.filter(assigned_to=user).exists():
            agent_user = user
            break
    
    if not agent_user:
        print("No users with assigned tickets found. Creating test assignment...")
        # Get first user and assign some tickets
        user = User.objects.first()
        if user:
            unassigned_tickets = Ticket.objects.filter(assigned_to__isnull=True)[:5]
            for ticket in unassigned_tickets:
                ticket.assigned_to = user
                ticket.save()
            agent_user = user
            print(f"Assigned 5 tickets to user: {user.username}")
        else:
            print("No users found in database")
            return
    
    print(f"Testing with user: {agent_user.username}")
    
    # Get assigned tickets
    assigned_tickets = Ticket.objects.filter(assigned_to=agent_user)
    total_assigned = assigned_tickets.count()
    print(f"Total assigned tickets: {total_assigned}")
    
    # Calculate priority distribution (same logic as in views.py)
    priority_defaults = {"Low": 0, "Medium": 0, "High": 0, "Critical": 0}
    
    for row in assigned_tickets.values('priority').annotate(count=Count('id')):
        key = row['priority']
        if key in priority_defaults:
            priority_defaults[key] = row['count']
    
    priority_counts = [
        priority_defaults["Low"],
        priority_defaults["Medium"], 
        priority_defaults["High"],
        priority_defaults["Critical"]
    ]
    
    print(f"\nPriority distribution for agent's tickets:")
    priorities = ['Low', 'Medium', 'High', 'Critical']
    for i, priority in enumerate(priorities):
        print(f"  {priority}: {priority_counts[i]}")
    
    # Test the JSON serialization (same as in views.py)
    import json
    priority_json = json.dumps(priority_counts)
    print(f"\nJSON data for frontend: {priority_json}")
    
    # Show sample tickets
    print(f"\nSample tickets assigned to agent:")
    for ticket in assigned_tickets[:5]:
        print(f"  {ticket.ticket_id}: {ticket.title[:30]}... (Priority: {ticket.priority})")
    
    print("\n✅ Priority data test completed successfully!")

if __name__ == "__main__":
    test_priority_data_directly()
