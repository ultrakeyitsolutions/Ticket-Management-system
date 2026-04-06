#!/usr/bin/env python
"""Script to check resolved tickets in the database"""
import os
import sys
import django

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from tickets.models import Ticket
from django.contrib.auth.models import User

def check_resolved_tickets():
    print("=== CHECKING RESOLVED TICKETS ===\n")
    
    # Count all tickets by status
    status_counts = {}
    all_tickets = Ticket.objects.all()
    
    print(f"Total tickets in database: {all_tickets.count()}")
    
    for status_choice in Ticket.STATUS_CHOICES:
        status_name = status_choice[0]
        count = Ticket.objects.filter(status=status_name).count()
        status_counts[status_name] = count
        print(f"{status_name}: {count}")
    
    print("\n=== DETAILED RESOLVED TICKETS ===")
    
    # Get all resolved tickets
    resolved_tickets = Ticket.objects.filter(status='Resolved').order_by('-updated_at')
    
    if resolved_tickets.exists():
        print(f"\nFound {resolved_tickets.count()} resolved tickets:\n")
        for ticket in resolved_tickets:
            print(f"ID: {ticket.ticket_id}")
            print(f"Title: {ticket.title}")
            print(f"Created by: {ticket.created_by.username}")
            print(f"Assigned to: {ticket.assigned_to.username if ticket.assigned_to else 'Unassigned'}")
            print(f"Priority: {ticket.priority}")
            print(f"Created: {ticket.created_at}")
            print(f"Updated: {ticket.updated_at}")
            print("-" * 50)
    else:
        print("\nNo resolved tickets found in the database!")
    
    print("\n=== RECENT TICKETS (Last 10) ===")
    
    recent_tickets = Ticket.objects.all().order_by('-updated_at')[:10]
    
    for ticket in recent_tickets:
        print(f"ID: {ticket.ticket_id} | Status: {ticket.status} | Priority: {ticket.priority} | Updated: {ticket.updated_at}")
    
    print("\n=== SAMPLE TICKET CREATION TEST ===")
    
    # Check if we should create a test resolved ticket
    if resolved_tickets.count() == 0:
        print("No resolved tickets found. Creating a test resolved ticket...")
        
        # Get or create a test user
        test_user, created = User.objects.get_or_create(
            username='testuser',
            defaults={
                'email': 'test@example.com',
                'first_name': 'Test',
                'last_name': 'User'
            }
        )
        
        # Create a resolved ticket
        test_ticket = Ticket.objects.create(
            ticket_id='TCKT-RESOLVED-001',
            title='Test Resolved Ticket',
            description='This is a test ticket that should appear as resolved',
            created_by=test_user,
            status='Resolved',
            priority='Medium'
        )
        
        print(f"Created test resolved ticket: {test_ticket.ticket_id}")
        print("Please refresh the admin dashboard to see this ticket.")

if __name__ == '__main__':
    check_resolved_tickets()
