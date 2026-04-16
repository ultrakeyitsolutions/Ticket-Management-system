#!/usr/bin/env python
import os
import sys

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

try:
    # Try importing from tickets app
    from tickets.models import Ticket, UserRating
    from django.contrib.auth.models import User
    from django.utils import timezone
    from django.db.models import Q
    
    print("=== MySQL Database Check (tickets app) ===")
    
    # Check total tickets
    total_tickets = Ticket.objects.count()
    print(f"Total tickets in database: {total_tickets}")
    
    if total_tickets == 0:
        print("No tickets found in database!")
        print("Let's check if the table exists and has data...")
        
        # Try to get table info
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SHOW TABLES LIKE '%ticket%';")
            tables = cursor.fetchall()
            print(f"Tables with 'ticket' in name: {tables}")
            
            if tables:
                table_name = tables[0][0]
                cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
                count = cursor.fetchone()[0]
                print(f"Records in {table_name}: {count}")
                
                cursor.execute(f"DESCRIBE {table_name};")
                columns = cursor.fetchall()
                print(f"Columns in {table_name}:")
                for col in columns:
                    print(f"  {col[0]} - {col[1]}")
        sys.exit(0)
    
    # Get all unique statuses
    statuses = Ticket.objects.values_list('status', flat=True).distinct()
    print(f"\nTicket statuses found: {list(statuses)}")
    
    # Check today's tickets
    today = timezone.now().date()
    print(f"\nChecking tickets for today: {today}")
    
    # Check agent users
    agent_users = User.objects.filter(is_staff=True)
    print(f"\nAgent users found: {agent_users.count()}")
    
    if agent_users.count() == 0:
        print("No agent users found! Creating a test agent...")
        # You might need to create an agent user first
        sys.exit(0)
    
    for agent in agent_users:
        print(f"\n--- Agent: {agent.username} (ID: {agent.id}) ---")
        
        # Check tickets assigned to this agent
        assigned = Ticket.objects.filter(assigned_to=agent)
        print(f"Total assigned tickets: {assigned.count()}")
        
        if assigned.count() == 0:
            print("No tickets assigned to this agent.")
            continue
        
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
        
        print(f"Resolved today (case-sensitive 'Resolved', 'Closed'): {resolved_today_v1}")
        print(f"Resolved today (lowercase 'resolved', 'closed'): {resolved_today_v2}")
        print(f"Resolved today (combined): {resolved_today_v3}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
