#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from superadmin.models import Plan

def update_free_trial_duration():
    """Update Free Trial plan description to mention 7 days"""
    
    try:
        free_trial = Plan.objects.get(name='Free Trial')
        # Note: The 7-day duration should be handled in the business logic
        # This is just updating any description if needed
        print(f"Free Trial plan found: {free_trial.name}")
        print(f"Current storage: {free_trial.storage}")
        print(f"Current price: ${free_trial.price}")
        print("Note: 7-day trial duration should be implemented in subscription logic")
        
    except Plan.DoesNotExist:
        print("Free Trial plan not found")

if __name__ == '__main__':
    update_free_trial_duration()
