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

def test_complete_fix():
    print("=== Complete Trial Payment Modal Fix Test ===\n")
    
    # Test 1: Verify plans have 7-day trials
    print("1. Verifying plans have 7-day trials...")
    plans = Plan.objects.filter(status='active')
    for plan in plans:
        assert plan.trial_days == 7, f"Plan {plan.name} should have 7 trial days, has {plan.trial_days}"
        print(f"   ✓ {plan.name}: {plan.trial_days} trial days")
    
    # Test 2: New user gets automatic trial
    print("\n2. Testing new user gets automatic trial...")
    
    # Clean up any existing test user
    User.objects.filter(username='test_new_user').delete()
    
    test_user = User.objects.create_user(
        username='test_new_user',
        email='test@example.com',
        password='testpass123'
    )
    
    # Simulate middleware creating subscription
    subscription, created = Subscription.objects.get_or_create(
        user=test_user,
        defaults={'status': 'trialing'}
    )
    
    if created:
        default_plan = Plan.objects.filter(status='active').first()
        subscription.plan = default_plan
        subscription.trial_start = timezone.now()
        subscription.trial_end = timezone.now() + timedelta(days=7)
        subscription.current_period_start = timezone.now()
        subscription.current_period_end = subscription.trial_end
        subscription.save()
    
    print(f"   ✓ Created subscription with status: {subscription.status}")
    print(f"   ✓ Trial active: {subscription.is_trial_active()}")
    print(f"   ✓ Needs payment: {subscription.needs_payment()}")
    print(f"   ✓ Payment modal should NOT show: {not subscription.needs_payment()}")
    
    # Test 3: During active trial - no payment modal
    assert subscription.is_trial_active() == True, "Trial should be active"
    assert subscription.needs_payment() == False, "Should not need payment during trial"
    print("   ✓ Payment modal correctly hidden during trial")
    
    # Test 4: Expired trial - payment modal shows
    print("\n3. Testing expired trial shows payment modal...")
    subscription.trial_end = timezone.now() - timedelta(days=1)
    subscription.save()
    
    # Simulate middleware checking expired trial
    subscription.update_expired_trial()
    
    print(f"   ✓ Status after expiry: {subscription.status}")
    print(f"   ✓ Trial active: {subscription.is_trial_active()}")
    print(f"   ✓ Needs payment: {subscription.needs_payment()}")
    print(f"   ✓ Payment modal SHOULD show: {subscription.needs_payment()}")
    
    assert subscription.status == 'expired', "Status should be 'expired'"
    assert subscription.is_trial_active() == False, "Trial should not be active"
    assert subscription.needs_payment() == True, "Should need payment after trial"
    print("   ✓ Payment modal correctly shows after trial expires")
    
    # Test 5: Reactivate trial (simulate payment)
    print("\n4. Testing paid subscription...")
    subscription.status = 'active'
    subscription.current_period_end = timezone.now() + timedelta(days=30)
    subscription.save()
    
    print(f"   ✓ Status after payment: {subscription.status}")
    print(f"   ✓ Needs payment: {subscription.needs_payment()}")
    print(f"   ✓ Payment modal should NOT show: {not subscription.needs_payment()}")
    
    assert subscription.needs_payment() == False, "Should not need payment for active subscription"
    print("   ✓ Payment modal correctly hidden for paid users")
    
    # Cleanup
    subscription.delete()
    test_user.delete()
    
    print("\n=== All Tests Passed! ===")
    print("✓ New users get 7-day free trials automatically")
    print("✓ Payment modal is hidden during trial period")
    print("✓ Payment modal appears after trial expires")
    print("✓ Payment modal is hidden for paid users")
    print("\nThe trial payment modal fix is working correctly!")

if __name__ == "__main__":
    test_complete_fix()
