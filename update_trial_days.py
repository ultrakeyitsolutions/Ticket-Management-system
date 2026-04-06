#!/usr/bin/env python
import os
import sys
import django

# Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Setup Django
django.setup()

from core.models import Plan

def update_trial_days():
    print("Updating trial days for existing plans...")
    plans = Plan.objects.all()
    
    for plan in plans:
        if plan.trial_days == 0:
            plan.trial_days = 7
            plan.save()
            print(f"Updated {plan.name}: Trial Days = {plan.trial_days}")
        else:
            print(f"{plan.name} already has {plan.trial_days} trial days")

if __name__ == "__main__":
    update_trial_days()
