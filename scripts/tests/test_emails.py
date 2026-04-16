#!/usr/bin/env python
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from users.models import UserProfile
from superadmin.views import _is_superadmin_user

print("=== Available SuperAdmin Emails for Testing ===")
print()

superadmin_users = []
for user in User.objects.all():
    if _is_superadmin_user(user):
        superadmin_users.append(user)
        print(f"Email: {user.email}")
        print(f"Username: {user.username}")
        print(f"Name: {user.first_name} {user.last_name}")
        print("-" * 40)

print(f"\nTotal SuperAdmin users found: {len(superadmin_users)}")

if superadmin_users:
    print("\nUse any of these emails to test the forgot password functionality:")
    print("http://127.0.0.1:8000/superadmin/forgot-password/")
else:
    print("\nNo SuperAdmin users found. Please create one first.")
