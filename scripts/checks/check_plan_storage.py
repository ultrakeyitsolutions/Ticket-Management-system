#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from superadmin.models import Plan
from django.db import connection

print("=== Plan Storage Analysis ===")

# 1. Database Table Information
print("\n1. DATABASE TABLE:")
print("Table Name: superadmin_plan")
print("Database: ticket_system (MySQL)")

# 2. Plan Model Fields
print("\n2. PLAN MODEL FIELDS:")
print("- id: AutoField (Primary Key)")
print("- name: CharField(max_length=100)")
print("- price: DecimalField(max_digits=10, decimal_places=2)")
print("- billing_cycle: CharField(choices=['monthly', 'yearly'])")
print("- users: PositiveIntegerField()")
print("- storage: CharField(max_length=50)")
print("- status: CharField(choices=['active', 'inactive'])")
print("- created_date: DateField(auto_now_add=True)")
print("- is_active: BooleanField(default=True)")

# 3. Current Plans in Database
print("\n3. CURRENT PLANS IN DATABASE:")
try:
    plans = Plan.objects.all()
    for plan in plans:
        print(f"ID: {plan.id}")
        print(f"Name: {plan.name}")
        print(f"Price: ₹{plan.price}")
        print(f"Billing: {plan.billing_cycle}")
        print(f"Users: {plan.users}")
        print(f"Storage: {plan.storage}")
        print(f"Status: {plan.status}")
        print(f"Created: {plan.created_date}")
        print(f"Active: {plan.is_active}")
        print("-" * 40)
except Exception as e:
    print(f"Error: {e}")

# 4. Database Connection Info
print("\n4. STORAGE LOCATION:")
print("Database Type: MySQL")
print("Host: localhost")
print("Port: 3306")
print("Database Name: ticket_system")
print("Table: superadmin_plan")

# 5. How Plans Are Used
print("\n5. HOW PLANS ARE USED:")
print("- Companies reference plans via Company.plan (ForeignKey)")
print("- Subscriptions reference plans via Subscription.plan (ForeignKey)")
print("- Payments reference plans via Payment.subscription.plan (ForeignKey)")
print("- Plans determine pricing and features for companies")

print("\n=== Storage Analysis Complete ===")
