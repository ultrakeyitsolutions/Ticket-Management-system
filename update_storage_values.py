#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from superadmin.models import Plan

def update_storage_values():
    """Update storage values to 1GB, 2GB, 3GB, 4GB, 10GB"""
    
    # Define the new storage values
    storage_mapping = {
        'Free Trial': '1GB',
        'Basic': '2GB', 
        'Standard': '3GB',
        'Premium': '4GB',
        'Unlimited': '10GB'
    }
    
    print("Updating storage values...")
    
    for plan_name, new_storage in storage_mapping.items():
        try:
            plan = Plan.objects.get(name=plan_name)
            old_storage = plan.storage
            plan.storage = new_storage
            plan.save()
            print(f"Updated {plan_name}: {old_storage} -> {new_storage}")
        except Plan.DoesNotExist:
            print(f"Plan '{plan_name}' not found")
    
    print("\nUpdated storage values:")
    for plan in Plan.objects.all().order_by('price'):
        print(f"- {plan.name}: {plan.storage}")

if __name__ == '__main__':
    update_storage_values()
