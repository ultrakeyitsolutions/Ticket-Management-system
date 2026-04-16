import sqlite3
import os
from datetime import datetime

# Connect to the database
db_path = os.path.join(os.path.dirname(__file__), 'db.sqlite3')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Show all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print("All tables in database:")
for table in tables:
    print(f"  {table[0]}")

# Find ticket-related tables
ticket_tables = [t[0] for t in tables if 'ticket' in t[0].lower()]
print(f"\nTicket-related tables: {ticket_tables}")

# Also check for users table
user_tables = [t[0] for t in tables if 'user' in t[0].lower() and 'auth' in t[0].lower()]
print(f"User-related tables: {user_tables}")

if ticket_tables:
    ticket_table = ticket_tables[0]
    print(f"\n--- {ticket_table} table structure ---")
    cursor.execute(f"PRAGMA table_info({ticket_table});")
    columns = cursor.fetchall()
    for col in columns:
        print(f"  {col[1]} ({col[2]})")

if ticket_tables:
    ticket_table = ticket_tables[0]
    
    print(f"\n--- Sample tickets from {ticket_table} ---")
    cursor.execute(f"SELECT * FROM {ticket_table} LIMIT 5;")
    tickets = cursor.fetchall()
    for ticket in tickets:
        print(f"  {ticket}")
    
    print(f"\n--- Tickets by status from {ticket_table} ---")
    cursor.execute(f"SELECT status, COUNT(*) FROM {ticket_table} GROUP BY status;")
    status_counts = cursor.fetchall()
    for status, count in status_counts:
        print(f"  {status}: {count}")
    
    print("\n--- Today's tickets ---")
    today = datetime.now().strftime('%Y-%m-%d')
    cursor.execute(f"SELECT ticket_id, status, assigned_to_id, updated_at FROM {ticket_table} WHERE DATE(updated_at) = '{today}';")
    today_tickets = cursor.fetchall()
    if today_tickets:
        for ticket in today_tickets:
            print(f"  ID: {ticket[0]}, Status: {ticket[1]}, Assigned: {ticket[2]}, Updated: {ticket[3]}")
    else:
        print("  No tickets updated today")

print("\n--- Agent users ---")
if user_tables:
    user_table = user_tables[0]
    cursor.execute(f"SELECT id, username, is_staff FROM {user_table} WHERE is_staff = 1;")
else:
    cursor.execute("SELECT id, username, is_staff FROM auth_user WHERE is_staff = 1;")
agents = cursor.fetchall()
for agent in agents:
    print(f"  ID: {agent[0]}, Username: {agent[1]}, Staff: {agent[2]}")
    
    if ticket_tables:
        ticket_table = ticket_tables[0]
        # Check tickets assigned to this agent
        cursor.execute(f"SELECT ticket_id, status, updated_at FROM {ticket_table} WHERE assigned_to_id = {agent[0]};")
        agent_tickets = cursor.fetchall()
        print(f"    Total assigned: {len(agent_tickets)}")
        
        # Check today's resolved/closed tickets
        cursor.execute(f"SELECT ticket_id, status, updated_at FROM {ticket_table} WHERE assigned_to_id = {agent[0]} AND DATE(updated_at) = '{today}' AND status IN ('Resolved', 'Closed');")
        resolved_today = cursor.fetchall()
        print(f"    Resolved today: {len(resolved_today)}")
        for ticket in resolved_today:
            print(f"      Ticket {ticket[0]}: {ticket[1]} at {ticket[2]}")

conn.close()
