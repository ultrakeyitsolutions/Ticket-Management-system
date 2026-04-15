#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from superadmin.models import Plan

def create_free_trial_plan():
    """Create Free Trial plan"""
    # Check if it already exists
    if Plan.objects.filter(name='Free Trial').exists():
        print("Free Trial plan already exists")
        return Plan.objects.get(name='Free Trial')
    
    free_trial = Plan.objects.create(
        name='Free Trial',
        price=0,
        billing_cycle='monthly',
        users=3,
        storage='5GB',
        status='active',
        is_active=True
    )
    print(f"Created Free Trial plan: {free_trial}")
    return free_trial

def create_unlimited_plan():
    """Create Unlimited plan"""
    # Check if it already exists
    if Plan.objects.filter(name='Unlimited').exists():
        print("Unlimited plan already exists")
        return Plan.objects.get(name='Unlimited')
    
    unlimited = Plan.objects.create(
        name='Unlimited',
        price=999,
        billing_cycle='monthly',
        users=999,
        storage='Unlimited',
        status='active',
        is_active=True
    )
    print(f"Created Unlimited plan: {unlimited}")
    return unlimited

if __name__ == '__main__':
    print("Creating Free Trial and Unlimited plans...")
    free_trial = create_free_trial_plan()
    unlimited = create_unlimited_plan()
    
    print("\nAll plans now available:")
    for plan in Plan.objects.all().order_by('price'):
        print(f"- {plan.name}: ${plan.price}/{plan.billing_cycle}, {plan.users} users, {plan.storage} storage")
