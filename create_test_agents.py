#!/usr/bin/env python
"""
Create test agents with different departments
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
    
    print("Creating test agents with different departments...")
    
    # Get or create Agent role
    agent_role, _ = Role.objects.get_or_create(name='Agent')
    
    # Create test agents with different departments
    test_agents = [
        {
            'username': 'tech_agent_1',
            'email': 'tech1@example.com',
            'password': 'testpass123',
            'department': 'Technical Support',
            'first_name': 'Tech',
            'last_name': 'Agent One'
        },
        {
            'username': 'tech_agent_2',
            'email': 'tech2@example.com',
            'password': 'testpass123',
            'department': 'Technical Support',
            'first_name': 'Tech',
            'last_name': 'Agent Two'
        },
        {
            'username': 'billing_agent_1',
            'email': 'billing1@example.com',
            'password': 'testpass123',
            'department': 'Billing Support',
            'first_name': 'Billing',
            'last_name': 'Agent One'
        },
        {
            'username': 'billing_agent_2',
            'email': 'billing2@example.com',
            'password': 'testpass123',
            'department': 'Billing Support',
            'first_name': 'Billing',
            'last_name': 'Agent Two'
        },
        {
            'username': 'general_agent_1',
            'email': 'general1@example.com',
            'password': 'testpass123',
            'department': 'General Support',
            'first_name': 'General',
            'last_name': 'Agent One'
        },
        {
            'username': 'general_agent_2',
            'email': 'general2@example.com',
            'password': 'testpass123',
            'department': 'General Support',
            'first_name': 'General',
            'last_name': 'Agent Two'
        }
    ]
    
    created_count = 0
    for agent_data in test_agents:
        # Check if user already exists
        if User.objects.filter(username=agent_data['username']).exists():
            print(f"User {agent_data['username']} already exists, skipping...")
            continue
        
        # Create user
        user = User.objects.create_user(
            username=agent_data['username'],
            email=agent_data['email'],
            password=agent_data['password'],
            first_name=agent_data['first_name'],
            last_name=agent_data['last_name']
        )
        
        # Create user profile with department
        profile = UserProfile.objects.create(
            user=user,
            role=agent_role,
            department=agent_data['department'],
            is_active=True
        )
        
        created_count += 1
        print(f"Created agent: {agent_data['username']} - {agent_data['department']}")
    
    print(f"\nSuccessfully created {created_count} test agents!")
    
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
    
    print("\nAgent filtering is now ready for testing!")
    
except Exception as e:
    print(f"Error creating test agents: {e}")
