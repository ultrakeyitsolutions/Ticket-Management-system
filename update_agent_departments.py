#!/usr/bin/env python
"""
Update existing agents to have proper departments
"""
import os
import sys
import django

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

try:
    from django.contrib.auth.models import User
    from users.models import UserProfile, Role
    
    print("Updating existing agents with departments...")
    
    # Get all users with Agent role
    agent_role = Role.objects.get(name='Agent')
    agents = User.objects.filter(
        userprofile__role=agent_role,
        is_active=True
    ).select_related('userprofile')
    
    # Department assignment strategy
    departments = ['Technical Support', 'Billing Support', 'General Support']
    dept_index = 0
    
    updated_count = 0
    for agent in agents:
        current_dept = agent.userprofile.department
        if not current_dept or current_dept not in departments:
            # Assign a department cyclically
            new_dept = departments[dept_index % len(departments)]
            agent.userprofile.department = new_dept
            agent.userprofile.save()
            print(f"Updated {agent.username}: {current_dept or 'None'} -> {new_dept}")
            updated_count += 1
            dept_index += 1
        else:
            print(f"{agent.username}: Already has department '{current_dept}'")
    
    print(f"\nSuccessfully updated {updated_count} agents!")
    
    # Display current agents by department
    print("\nCurrent agents by department:")
    agents = User.objects.filter(
        userprofile__role__name='Agent',
        is_active=True
    ).select_related('userprofile').order_by('userprofile__department', 'username')
    
    current_dept = None
    for agent in agents:
        dept = agent.userprofile.department or 'No Department'
        if dept != current_dept:
            if current_dept:
                print("")
            print(f"\n{dept}:")
            current_dept = dept
        print(f"  - {agent.username} ({agent.first_name} {agent.last_name})")
    
    print("\nAgent department assignment is ready!")
    
except Exception as e:
    print(f"Error updating agents: {e}")
