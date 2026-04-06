#!/usr/bin/env python
"""
Debug script to analyze ticket data and fix chart logic
"""
import os
import sys
import django
from datetime import datetime, timedelta

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.utils import timezone
from tickets.models import Ticket

def debug_ticket_data():
    """Debug ticket data to understand why 30 days shows 0"""
    print("=== Ticket Data Debug Analysis ===\n")
    
    # Get all tickets with their creation dates
    all_tickets = Ticket.objects.all().order_by('-created_at')
    total_count = all_tickets.count()
    
    print(f"Total tickets in database: {total_count}")
    
    # Show ticket creation dates
    print("\n📅 Ticket Creation Dates (most recent first):")
    for i, ticket in enumerate(all_tickets[:10]):  # Show first 10
        print(f"  {i+1}. {ticket.ticket_id} - {ticket.created_at} ({ticket.created_at.date()})")
    
    # Check tickets in last 30 days
    now = timezone.now()
    thirty_days_ago = now - timedelta(days=30)
    
    recent_tickets = Ticket.objects.filter(created_at__gte=thirty_days_ago)
    recent_count = recent_tickets.count()
    
    print(f"\n📊 Tickets in last 30 days: {recent_count}")
    
    # Check tickets by date range
    print("\n🔍 Checking date ranges:")
    print(f"  Current time: {now}")
    print(f"  30 days ago: {thirty_days_ago}")
    
    # Manual date filtering test
    from datetime import date
    today = now.date()
    tickets_today = Ticket.objects.filter(created_at__date=today).count()
    print(f"  Tickets today ({today}): {tickets_today}")
    
    # Check last 7 days manually
    for i in range(7):
        check_date = (now - timedelta(days=i)).date()
        day_count = Ticket.objects.filter(created_at__date=check_date).count()
        print(f"  {check_date}: {day_count} tickets")
    
    # Check if tickets exist at all
    if total_count > 0:
        oldest_ticket = all_tickets.last()
        newest_ticket = all_tickets.first()
        print(f"\n📈 Date Range:")
        print(f"  Oldest ticket: {oldest_ticket.created_at}")
        print(f"  Newest ticket: {newest_ticket.created_at}")
        
        # Check if tickets are in the expected time range
        days_diff = (now - oldest_ticket.created_at).days
        print(f"  Days span: {days_diff}")
        
        if days_diff > 30:
            print(f"  ⚠️  WARNING: All tickets are older than 30 days!")
            print(f"  This explains why 30-day chart shows 0")
    
    print("\n✅ Analysis complete")

if __name__ == '__main__':
    debug_ticket_data()
