#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from tickets.models import UserRating, Ticket
from django.contrib.auth.models import User

# Check existing data
print('=== Database Check ===')
print(f'Existing ratings: {UserRating.objects.count()}')
print(f'Existing tickets: {Ticket.objects.count()}')
print(f'Existing users: {User.objects.count()}')

# Show sample data
if UserRating.objects.exists():
    print('\n=== Sample Ratings ===')
    for rating in UserRating.objects.all()[:5]:
        print(f'{rating.user.username} - {rating.rating}/5 - {rating.title}')

if Ticket.objects.exists():
    print('\n=== Sample Tickets ===')
    for ticket in Ticket.objects.all()[:5]:
        print(f'{ticket.ticket_id} - {ticket.title} (by {ticket.created_by.username})')

# Create test data if needed
if UserRating.objects.count() == 0 and Ticket.objects.count() > 0:
    print('\n=== Creating Test Rating ===')
    user = User.objects.first()
    ticket = Ticket.objects.first()
    
    UserRating.objects.create(
        user=user,
        agent=ticket.assigned_to,
        ticket_reference=ticket.ticket_id,
        rating=4,
        title='Great service!',
        content='The support team was very helpful and resolved my issue quickly.',
        recommend=True
    )
    print('Test rating created successfully!')
