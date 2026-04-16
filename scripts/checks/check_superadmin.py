#!/usr/bin/env python
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from users.models import UserProfile, Role
from superadmin.views import _is_superadmin_user

print("Checking SuperAdmin setup...")

# Check existing superadmin users
users = User.objects.filter(is_superuser=True)
print(f"Found {users.count()} superusers:")
for user in users:
    print(f"  - {user.username} ({user.email})")

# Check test user specifically
test_user = User.objects.filter(email='superadmin@test.com').first()
if test_user:
    print(f"\nTest user found: {test_user.username}")
    print(f"Is superuser: {test_user.is_superuser}")
    print(f"Is staff: {test_user.is_staff}")
    print(f"_is_superadmin_user: {_is_superadmin_user(test_user)}")
    
    try:
        profile = test_user.userprofile
        print(f"Profile role: {profile.role.name if profile.role else 'No role'}")
    except UserProfile.DoesNotExist:
        print("No profile found")
else:
    print("\nTest user not found")

print("\nForgot password URLs should be:")
print("  - http://127.0.0.1:8000/superadmin/forgot-password/")
print("  - http://127.0.0.1:8000/superadmin/reset-password/")
