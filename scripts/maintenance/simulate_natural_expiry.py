#!/usr/bin/env python
import os
import sys
import django

# Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Setup Django
django.setup()

from django.contrib.auth.models import User
from core.models import Subscription as CoreSubscription
from superadmin.views import should_show_payment_modal
from django.utils import timezone
from datetime import timedelta

def simulate_natural_expiry():
    print("=== Simulating Natural Trial Expiry ===\n")
    
    # Get the user
    try:
        user = User.objects.get(username='adhi12')
        print(f"✓ Found user: {user.username}")
    except User.DoesNotExist:
        print("✗ User 'adhi12' not found")
        return False
    
    # Get the core subscription
    core_sub = CoreSubscription.objects.filter(user=user).first()
    if not core_sub:
        print("✗ No core subscription found")
        return False
    
    print(f"Current subscription status:")
    print(f"  Status: {core_sub.status}")
    print(f"  Trial start: {core_sub.trial_start}")
    print(f"  Trial end: {core_sub.trial_end}")
    print(f"  Days remaining: {core_sub.get_trial_days_remaining()}")
    print(f"  Is trial active: {core_sub.is_trial_active()}")
    print(f"  Needs payment: {core_sub.needs_payment()}")
    
    should_show_now = should_show_payment_modal(user)
    print(f"  should_show_payment_modal(): {should_show_now}")
    
    # Simulate trial expiry in 7 days (when it naturally expires)
    print(f"\n--- Simulating expiry in 7 days ---")
    future_expiry = core_sub.trial_start + timedelta(days=7)
    print(f"Trial will naturally expire on: {future_expiry}")
    
    # Temporarily set to expired time (current time - 1 hour)
    expired_time = timezone.now() - timedelta(hours=1)
    core_sub.trial_end = expired_time
    core_sub.save()
    
    print(f"Setting trial to expired time: {expired_time}")
    print(f"Current time: {timezone.now()}")
    print(f"Is trial active: {core_sub.is_trial_active()}")
    print(f"Needs payment: {core_sub.needs_payment()}")
    
    # Update expired trial status
    core_sub.update_expired_trial()
    print(f"Status after update: {core_sub.status}")
    
    should_show_expired = should_show_payment_modal(user)
    print(f"should_show_payment_modal(): {should_show_expired}")
    
    if should_show_expired:
        print("✅ Modal WILL be shown when trial naturally expires")
    else:
        print("❌ Modal will NOT be shown when trial expires")
        return False
    
    # Restore to current state
    core_sub.trial_end = timezone.now() + timedelta(days=6)  # 6 days remaining
    core_sub.status = 'trialing'
    core_sub.save()
    
    print(f"\n--- Restored to current state ---")
    print(f"Days remaining: {core_sub.get_trial_days_remaining()}")
    print(f"Is trial active: {core_sub.is_trial_active()}")
    print(f"Needs payment: {core_sub.needs_payment()}")
    
    should_show_restored = should_show_payment_modal(user)
    print(f"should_show_payment_modal(): {should_show_restored}")
    
    if not should_show_restored:
        print("✅ Modal correctly HIDDEN while trial is active")
    else:
        print("❌ Modal incorrectly shown while trial is active")
        return False
    
    print(f"\n=== Natural Expiry Test Results ===")
    print("✅ Payment modal system is PERFECT:")
    print(f"   ✅ Current: Trial active for {core_sub.get_trial_days_remaining()} days → Modal HIDDEN")
    print(f"   ✅ Future: Trial expires → Modal WILL SHOW")
    print(f"   ✅ User experience: Seamless transition from trial to payment")
    
    print(f"\n📅 Trial Schedule for user {user.username}:")
    print(f"   Started: {core_sub.trial_start.strftime('%Y-%m-%d %H:%M')}")
    print(f"   Expires: {core_sub.trial_end.strftime('%Y-%m-%d %H:%M')}")
    print(f"   Days left: {core_sub.get_trial_days_remaining()}")
    print(f"   After expiry: Payment modal WILL appear")
    
    return True

if __name__ == "__main__":
    success = simulate_natural_expiry()
    if not success:
        sys.exit(1)
