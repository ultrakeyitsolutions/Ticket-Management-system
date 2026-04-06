#!/usr/bin/env python
import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from tickets.models import Ticket

def debug_agent_data():
    print("=== Debug Agent Data ===")
    
    # Get the agent user
    agent_user = User.objects.filter(username='yash').first()
    if not agent_user:
        print("User 'yash' not found")
        return
    
    print(f"Agent: {agent_user.username}")
    print(f"  is_staff: {agent_user.is_staff}")
    
    # Check profile
    try:
        profile = agent_user.userprofile
        print(f"  Profile role: {profile.role}")
    except:
        print("  No profile found")
    
    # Get assigned tickets
    assigned_tickets = Ticket.objects.filter(assigned_to=agent_user)
    print(f"  Assigned tickets: {assigned_tickets.count()}")
    
    # Show ticket priorities
    for ticket in assigned_tickets:
        print(f"    {ticket.ticket_id}: {ticket.priority}")
    
    # Calculate priority distribution exactly like in the view
    from django.db.models import Count
    priority_defaults = {"Low": 0, "Medium": 0, "High": 0, "Critical": 0}
    
    for row in assigned_tickets.values('priority').annotate(c=Count('id')):
        key = row['priority']
        if key in priority_defaults:
            priority_defaults[key] = row['c']
    
    priority_counts = [
        priority_defaults["Low"],
        priority_defaults["Medium"],
        priority_defaults["High"],
        priority_defaults["Critical"]
    ]
    
    print(f"Priority counts: {priority_counts}")
    print(f"Total: {sum(priority_counts)}")
    
    # Test JSON serialization
    import json
    priority_json = json.dumps(priority_counts)
    print(f"JSON: {priority_json}")

if __name__ == "__main__":
    debug_agent_data()
