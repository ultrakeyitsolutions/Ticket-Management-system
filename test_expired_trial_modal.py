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

def test_expired_trial_modal():
    print("=== Testing Payment Modal After Trial Ends ===\n")
    
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
    
    # Store original trial end date
    original_trial_end = core_sub.trial_end
    print(f"Original trial end: {original_trial_end}")
    
    print("\n1. Testing BEFORE trial expires...")
    print(f"   Trial end: {core_sub.trial_end}")
    print(f"   Current time: {timezone.now()}")
    print(f"   Is trial active: {core_sub.is_trial_active()}")
    print(f"   Needs payment: {core_sub.needs_payment()}")
    
    should_show_before = should_show_payment_modal(user)
    print(f"   should_show_payment_modal(): {should_show_before}")
    
    if not should_show_before:
        print("   ✅ Modal correctly HIDDEN during trial")
    else:
        print("   ❌ Modal incorrectly shown during trial")
        return False
    
    print("\n2. Testing AFTER trial expires...")
    # Set trial to expired
    expired_time = timezone.now() - timedelta(days=1)
    core_sub.trial_end = expired_time
    core_sub.save()
    
    print(f"   Set trial end to: {expired_time}")
    print(f"   Current time: {timezone.now()}")
    print(f"   Is trial active: {core_sub.is_trial_active()}")
    print(f"   Needs payment: {core_sub.needs_payment()}")
    
    # Update expired trial status
    core_sub.update_expired_trial()
    print(f"   Status after update: {core_sub.status}")
    print(f"   Is trial active: {core_sub.is_trial_active()}")
    print(f"   Needs payment: {core_sub.needs_payment()}")
    
    should_show_after = should_show_payment_modal(user)
    print(f"   should_show_payment_modal(): {should_show_after}")
    
    if should_show_after:
        print("   ✅ Modal correctly SHOWN after trial expires")
        success = True
    else:
        print("   ❌ Modal incorrectly hidden after trial expires")
        success = False
    
    print("\n3. Testing restore trial...")
    # Restore original trial end
    core_sub.trial_end = original_trial_end
    core_sub.status = 'trialing'
    core_sub.save()
    
    print(f"   Restored trial end: {core_sub.trial_end}")
    print(f"   Status: {core_sub.status}")
    print(f"   Is trial active: {core_sub.is_trial_active()}")
    print(f"   Needs payment: {core_sub.needs_payment()}")
    
    should_show_restored = should_show_payment_modal(user)
    print(f"   should_show_payment_modal(): {should_show_restored}")
    
    if not should_show_restored:
        print("   ✅ Modal correctly HIDDEN after restoring trial")
    else:
        print("   ❌ Modal incorrectly shown after restoring trial")
        success = False
    
    print(f"\n=== Test Results ===")
    if success:
        print("✅ Payment modal behavior is CORRECT:")
        print("   - Hidden during valid trial period")
        print("   - Shown after trial expires")
        print("   - Hidden when trial is restored")
        print("\n🎉 The payment modal system works perfectly!")
    else:
        print("❌ Payment modal behavior needs attention")
    
    return success

if __name__ == "__main__":
    success = test_expired_trial_modal()
    if not success:
        sys.exit(1)
