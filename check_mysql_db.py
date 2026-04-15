#!/usr/bin/env python
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

try:
    django.setup()
    
    from django.contrib.auth.models import User
    from apps.core.models import Ticket
    from django.utils import timezone
    from django.db.models import Q
    
    print("=== MySQL Database Check ===")
    
    # Check if Ticket model can be imported
    try:
        print(f"Total tickets in database: {Ticket.objects.count()}")
    except Exception as e:
        print(f"Error accessing Ticket model: {e}")
        # Try alternative import
        try:
            from tickets.models import Ticket as AltTicket
            print(f"Total tickets (alternative import): {AltTicket.objects.count()}")
            Ticket = AltTicket
        except Exception as e2:
            print(f"Alternative import also failed: {e2}")
            sys.exit(1)
    
    # Get all unique statuses
    statuses = Ticket.objects.values_list('status', flat=True).distinct()
    print(f"\nTicket statuses: {list(statuses)}")
    
    # Check today's tickets
    today = timezone.now().date()
    print(f"\nChecking tickets for today: {today}")
    
    # Check agent users
    agent_users = User.objects.filter(is_staff=True)
    print(f"\nAgent users: {agent_users.count()}")
    
    for agent in agent_users:
        print(f"\n--- Agent: {agent.username} (ID: {agent.id}) ---")
        
        # Check tickets assigned to this agent
        assigned = Ticket.objects.filter(assigned_to=agent)
        print(f"Total assigned tickets: {assigned.count()}")
        
        # Check tickets updated today
        today_updated = assigned.filter(updated_at__date=today)
        print(f"Tickets updated today: {today_updated.count()}")
        
        # Show today's tickets with details
        for ticket in today_updated:
            print(f"  Ticket {ticket.ticket_id}: status='{ticket.status}', updated_at={ticket.updated_at}")
        
        # Check resolved/closed tickets with different approaches
        resolved_today_v1 = assigned.filter(status__in=['Resolved', 'Closed'], updated_at__date=today).count()
        resolved_today_v2 = assigned.filter(status__in=['resolved', 'closed'], updated_at__date=today).count()
        resolved_today_v3 = assigned.filter(
            Q(status__in=['Resolved', 'Closed', 'resolved', 'closed']) &
            Q(updated_at__date=today)
        ).count()
        
        print(f"Resolved today (case-sensitive): {resolved_today_v1}")
        print(f"Resolved today (lowercase): {resolved_today_v2}")
        print(f"Resolved today (combined): {resolved_today_v3}")
        
        # Check if there's a resolved_at field
        try:
            resolved_today_v4 = assigned.filter(resolved_at__date=today).count()
            print(f"Resolved today (by resolved_at field): {resolved_today_v4}")
        except:
            print("No resolved_at field found")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
