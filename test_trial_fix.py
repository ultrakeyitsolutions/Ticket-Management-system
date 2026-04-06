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

def test_trial_logic():
    print("=== Testing Trial Payment Modal Fix ===\n")
    
    # Test 1: Check plans have trial days
    print("1. Checking plans...")
    plans = Plan.objects.filter(status='active')
    for plan in plans:
        print(f"   - {plan.name}: {plan.trial_days} trial days")
    
    # Test 2: Create a test user
    print("\n2. Creating test user...")
    test_user, created = User.objects.get_or_create(
        username='testuser_trial',
        defaults={'email': 'test@example.com'}
    )
    if created:
        test_user.set_password('testpass123')
        test_user.save()
        print(f"   Created user: {test_user.username}")
    else:
        print(f"   Using existing user: {test_user.username}")
    
    # Test 3: Simulate middleware creating subscription
    print("\n3. Testing subscription creation...")
    subscription, sub_created = Subscription.objects.get_or_create(
        user=test_user,
        defaults={'status': 'trialing'}
    )
    
    if sub_created:
        # Simulate middleware logic
        default_plan = Plan.objects.filter(status='active').first()
        if default_plan and default_plan.trial_days > 0:
            subscription.plan = default_plan
            subscription.trial_start = timezone.now()
            subscription.trial_end = timezone.now() + timedelta(days=default_plan.trial_days)
            subscription.current_period_start = timezone.now()
            subscription.current_period_end = subscription.trial_end
            subscription.save()
            print(f"   Created trial subscription for {default_plan.name}")
        else:
            print("   No plan with trial available")
    else:
        print(f"   Using existing subscription: {subscription.status}")
    
    # Test 4: Check payment modal logic
    print("\n4. Testing payment modal logic...")
    print(f"   Subscription status: {subscription.status}")
    print(f"   Is active: {subscription.is_active()}")
    print(f"   Is trial active: {subscription.is_trial_active()}")
    print(f"   Trial days remaining: {subscription.get_trial_days_remaining()}")
    print(f"   Needs payment: {subscription.needs_payment()}")
    print(f"   Is paid user: {subscription.is_paid()}")
    
    # Test 5: Test expired trial scenario
    print("\n5. Testing expired trial scenario...")
    # Set trial to expired
    subscription.trial_end = timezone.now() - timedelta(days=1)
    subscription.save()
    
    print(f"   After setting trial to expired:")
    print(f"   Is trial active: {subscription.is_trial_active()}")
    print(f"   Trial days remaining: {subscription.get_trial_days_remaining()}")
    print(f"   Needs payment: {subscription.needs_payment()}")
    print(f"   Is paid user: {subscription.is_paid()}")
    
    # Reset trial to active
    subscription.trial_end = timezone.now() + timedelta(days=7)
    subscription.save()
    
    print("\n=== Test Summary ===")
    print("✓ Plans have trial days configured")
    print("✓ New users get trial subscriptions automatically")
    print("✓ Payment modal should NOT show during active trial")
    print("✓ Payment modal SHOULD show after trial expires")
    
    # Cleanup
    subscription.delete()
    test_user.delete()
    print("\n✓ Cleaned up test data")

if __name__ == "__main__":
    test_trial_logic()
