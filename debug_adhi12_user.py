#!/usr/bin/env python
import os
import sys
import django

# Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Setup Django
django.setup()

from django.contrib.auth.models import User
from core.models import Plan, Subscription
from django.utils import timezone
from datetime import timedelta

def debug_adhi12_user():
    print("=== Debugging adhi12 User ===\n")
    
    # Get the user
    try:
        user = User.objects.get(username='adhi12')
        print(f"✓ Found user: {user.username}")
        print(f"  Email: {user.email}")
        print(f"  Is active: {user.is_active}")
        print(f"  Date joined: {user.date_joined}")
    except User.DoesNotExist:
        print("✗ User 'adhi12' not found")
        return
    
    # Check subscription
    print("\n--- Subscription Details ---")
    try:
        subscription = Subscription.objects.get(user=user)
        print(f"✓ Found subscription:")
        print(f"  Status: {subscription.status}")
        print(f"  Plan: {subscription.plan.name if subscription.plan else 'No Plan'}")
        print(f"  Trial start: {subscription.trial_start}")
        print(f"  Trial end: {subscription.trial_end}")
        print(f"  Current period start: {subscription.current_period_start}")
        print(f"  Current period end: {subscription.current_period_end}")
        
        # Check subscription methods
        print(f"\n--- Subscription Method Results ---")
        print(f"  is_active(): {subscription.is_active()}")
        print(f"  is_trial_active(): {subscription.is_trial_active()}")
        print(f"  needs_payment(): {subscription.needs_payment()}")
        print(f"  is_paid(): {subscription.is_paid()}")
        print(f"  get_trial_days_remaining(): {subscription.get_trial_days_remaining()}")
        
        # Check if trial should be active
        if subscription.trial_end:
            now = timezone.now()
            is_trial_valid = now < subscription.trial_end
            print(f"\n--- Trial Validation ---")
            print(f"  Current time: {now}")
            print(f"  Trial end: {subscription.trial_end}")
            print(f"  Is trial still valid: {is_trial_valid}")
            
            if is_trial_valid:
                days_remaining = subscription.get_trial_days_remaining()
                print(f"  Days remaining: {days_remaining}")
                print(f"  Expected: needs_payment() = False")
            else:
                print(f"  Trial has expired")
                print(f"  Expected: needs_payment() = True")
        
        # Check if we need to update expired trial
        print(f"\n--- Update Expired Trial ---")
        was_updated = subscription.update_expired_trial()
        print(f"  Was updated: {was_updated}")
        print(f"  New status: {subscription.status}")
        print(f"  New needs_payment(): {subscription.needs_payment()}")
        
    except Subscription.DoesNotExist:
        print("✗ No subscription found for user")
        
        # Create one if it doesn't exist
        print("\n--- Creating Trial Subscription ---")
        default_plan = Plan.objects.filter(status='active').first()
        if default_plan:
            subscription = Subscription.objects.create(
                user=user,
                plan=default_plan,
                status='trialing',
                trial_start=timezone.now(),
                trial_end=timezone.now() + timedelta(days=7),
                current_period_start=timezone.now(),
                current_period_end=timezone.now() + timedelta(days=7)
            )
            print(f"✓ Created trial subscription:")
            print(f"  Status: {subscription.status}")
            print(f"  Plan: {subscription.plan.name}")
            print(f"  Trial end: {subscription.trial_end}")
            print(f"  needs_payment(): {subscription.needs_payment()}")
        else:
            print("✗ No active plans found")
    
    # Check available plans
    print(f"\n--- Available Plans ---")
    plans = Plan.objects.filter(status='active')
    for plan in plans:
        print(f"  - {plan.name}: {plan.trial_days} trial days, Status: {plan.status}")

if __name__ == "__main__":
    debug_adhi12_user()
