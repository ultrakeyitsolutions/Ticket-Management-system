#!/usr/bin/env python
import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from tickets.models import Ticket
from users.models import UserProfile

def check_user_roles():
    print("=== Checking User Roles ===")
    
    # Check users and their profiles
    for user in User.objects.all():
        print(f"\nUser: {user.username}")
        print(f"  is_superuser: {user.is_superuser}")
        print(f"  is_staff: {user.is_staff}")
        
        # Check if user has profile
        try:
            profile = user.userprofile
            if hasattr(profile, 'role') and profile.role:
                print(f"  Profile role: {profile.role}")
            else:
                print(f"  Profile role: None")
        except UserProfile.DoesNotExist:
            print(f"  Profile: Does not exist")
        except Exception as e:
            print(f"  Profile error: {e}")
        
        # Check assigned tickets
        assigned_count = Ticket.objects.filter(assigned_to=user).count()
        print(f"  Assigned tickets: {assigned_count}")
    
    # Check if there are any roles defined
    print(f"\n=== Available Roles ===")
    try:
        from users.models import Role
        roles = Role.objects.all()
        for role in roles:
            print(f"Role: {role.name}")
    except Exception as e:
        print(f"Error checking roles: {e}")

if __name__ == "__main__":
    check_user_roles()
