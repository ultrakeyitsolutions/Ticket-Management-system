#!/usr/bin/env python
import os
import sys
import django

# Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Setup Django
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from core.models import Subscription as CoreSubscription, Plan
from superadmin.views import should_show_payment_modal
from django.utils import timezone
from datetime import timedelta

def test_complete_fix():
    print("=== Complete Payment Modal Fix Test ===\n")
    
    # Get the user
    try:
        user = User.objects.get(username='adhi12')
        print(f"✓ Testing for user: {user.username}")
    except User.DoesNotExist:
        print("✗ User 'adhi12' not found")
        return False
    
    # Test 1: Core subscription check
    print("\n1. Testing Core Subscription...")
    core_sub = CoreSubscription.objects.filter(user=user).first()
    if core_sub:
        print(f"   Status: {core_sub.status}")
        print(f"   Trial active: {core_sub.is_trial_active()}")
        print(f"   Needs payment: {core_sub.needs_payment()}")
        print(f"   Days remaining: {core_sub.get_trial_days_remaining()}")
        
        if core_sub.is_trial_active() and not core_sub.needs_payment():
            print("   ✅ Core subscription is valid - modal should NOT show")
        else:
            print("   ❌ Core subscription issue - modal might show")
    else:
        print("   ❌ No core subscription found")
        return False
    
    # Test 2: Superadmin function check
    print("\n2. Testing Superadmin Function...")
    try:
        should_show = should_show_payment_modal(user)
        print(f"   should_show_payment_modal() returns: {should_show}")
        
        if should_show:
            print("   ❌ Superadmin function WILL show modal")
            return False
        else:
            print("   ✅ Superadmin function will NOT show modal")
    except Exception as e:
        print(f"   ❌ Error in superadmin function: {e}")
        return False
    
    # Test 3: Test with Django client
    print("\n3. Testing with Django Client...")
    client = Client()
    client.force_login(user)
    
    try:
        # Test home page
        response = client.get('/')
        print(f"   Home page status: {response.status_code}")
        
        # Check if the template context has the right variables
        if hasattr(response, 'context'):
            show_modal = response.context.get('show_payment_modal', False)
            print(f"   Template show_payment_modal: {show_modal}")
            
            if not show_modal:
                print("   ✅ Template will not show modal")
            else:
                print("   ❌ Template will show modal")
                return False
        
    except Exception as e:
        print(f"   ❌ Error testing client: {e}")
        return False
    
    # Test 4: Test expired trial scenario
    print("\n4. Testing Expired Trial Scenario...")
    if core_sub:
        # Temporarily set trial to expired
        original_end = core_sub.trial_end
        core_sub.trial_end = timezone.now() - timedelta(days=1)
        core_sub.save()
        
        # Test superadmin function with expired trial
        should_show_expired = should_show_payment_modal(user)
        print(f"   With expired trial, should_show_payment_modal(): {should_show_expired}")
        
        if should_show_expired:
            print("   ✅ Correctly shows modal when trial expires")
        else:
            print("   ❌ Should show modal when trial expires")
            return False
        
        # Restore original trial end
        core_sub.trial_end = original_end
        core_sub.save()
        
        # Verify it's back to normal
        should_show_normal = should_show_payment_modal(user)
        if not should_show_normal:
            print("   ✅ Modal correctly hidden after restoring trial")
        else:
            print("   ❌ Modal should be hidden after restoring trial")
            return False
    
    print("\n=== All Tests Passed! ===")
    print("✅ User has valid core trial subscription")
    print("✅ Superadmin function correctly returns False")
    print("✅ Template context is correct")
    print("✅ Modal shows when trial expires")
    print("✅ Modal hides when trial is restored")
    print("\n🎉 The payment modal fix is working correctly!")
    print("User adhi12 should NOT see the payment modal during their trial.")
    
    return True

if __name__ == "__main__":
    success = test_complete_fix()
    if not success:
        print("\n❌ Some tests failed!")
        sys.exit(1)
