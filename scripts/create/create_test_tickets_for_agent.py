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
from users.models import Role
import datetime
from django.utils import timezone

def create_test_tickets():
    print("=== CREATING TEST TICKETS FOR AGENT ===\n")
    
    # Find an agent user
    agent_user = User.objects.filter(
        userprofile__role__name__iexact='agent'
    ).first()
    
    if not agent_user:
        print("No agent user found! Creating one...")
        # Create agent role if it doesn't exist
        agent_role, created = Role.objects.get_or_create(
            name='Agent',
            defaults={'description': 'Agent role for ticket management'}
        )
        
        # Create a test agent user
        agent_user = User.objects.create_user(
            username='testagent_reports',
            email='testagent@example.com',
            first_name='Test',
            last_name='Agent',
            password='testpass123'
        )
        
        # Assign agent role
        from users.models import UserProfile
        profile, created = UserProfile.objects.get_or_create(
            user=agent_user,
            defaults={'role': agent_role}
        )
        if not created:
            profile.role = agent_role
            profile.save()
    
    print(f"Using agent: {agent_user.username}")
    
    # Create test tickets with different statuses
    test_tickets = [
        {
            'title': 'Login Issue - Customer Cannot Access',
            'description': 'Customer is unable to log into their account',
            'status': 'Open',
            'priority': 'High'
        },
        {
            'title': 'Payment Processing Error',
            'description': 'Customer reports payment gateway errors',
            'status': 'In Progress',
            'priority': 'Critical'
        },
        {
            'title': 'Password Reset Request',
            'description': 'Customer needs password reset assistance',
            'status': 'Resolved',
            'priority': 'Medium'
        },
        {
            'title': 'Account Update Problem',
            'description': 'Customer cannot update profile information',
            'status': 'Resolved',
            'priority': 'Low'
        },
        {
            'title': 'Feature Request - New Dashboard',
            'description': 'Customer requests new dashboard features',
            'status': 'In Progress',
            'priority': 'Medium'
        }
    ]
    
    created_count = 0
    for i, ticket_data in enumerate(test_tickets, 1):
        # Generate a unique ticket ID
        ticket_id = f"TEST-{i:03d}"
        
        # Check if ticket already exists
        if Ticket.objects.filter(ticket_id=ticket_id).exists():
            print(f"Ticket {ticket_id} already exists, skipping...")
            continue
        
        # Create the ticket
        ticket = Ticket.objects.create(
            ticket_id=ticket_id,
            title=ticket_data['title'],
            description=ticket_data['description'],
            status=ticket_data['status'],
            priority=ticket_data['priority'],
            assigned_to=agent_user,
            created_by=agent_user,  # Agent creates the ticket for testing
            created_at=timezone.now() - datetime.timedelta(hours=i),
            updated_at=timezone.now() - datetime.timedelta(minutes=i*10)
        )
        
        created_count += 1
        print(f"Created ticket: {ticket.ticket_id} - {ticket.status}")
    
    print(f"\n=== SUMMARY ===")
    print(f"Created {created_count} new test tickets for agent {agent_user.username}")
    
    # Show current status counts
    print(f"\nCurrent ticket status counts:")
    for status in ['Open', 'In Progress', 'Resolved', 'Closed']:
        count = Ticket.objects.filter(assigned_to=agent_user, status=status).count()
        print(f"{status}: {count}")
    
    total = Ticket.objects.filter(assigned_to=agent_user).count()
    print(f"Total: {total}")
    
    if total > 0:
        print(f"\nPercentages:")
        for status in ['Open', 'In Progress', 'Resolved', 'Closed']:
            count = Ticket.objects.filter(assigned_to=agent_user, status=status).count()
            pct = round((count / total) * 100, 1)
            print(f"{status}: {pct}%")

if __name__ == '__main__':
    create_test_tickets()
