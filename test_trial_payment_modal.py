#!/usr/bin/env python
"""
Test script to verify payment modal fix for trial users.
This script tests the should_show_payment_modal function with different scenarios.
"""

import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ticket_management.settings')
django.setup()

from django.utils import timezone
from superadmin.models import Subscription, Company, Plan
from superadmin.views import should_show_payment_modal
from django.contrib.auth.models import User
from users.models import UserProfile

def test_payment_modal_fix():
    """Test payment modal logic for trial users"""
    print("=== Testing Payment Modal Fix for Trial Users ===")
    
    # Get current trial subscriptions
    trial_subscriptions = Subscription.objects.filter(status='trial')
    print(f"Found {trial_subscriptions.count()} trial subscriptions")
    
    for subscription in trial_subscriptions:
        print(f"\n--- Testing Subscription {subscription.id} ---")
        print(f"Status: {subscription.status}")
        print(f"End Date: {subscription.end_date}")
        print(f"Trial End Date: {subscription.trial_end_date}")
        print(f"Is Trial Active: {subscription.is_trial_active}")
        print(f"Trial Days Remaining: {subscription.trial_days_remaining}")
        
        # Get users for this company
        company = subscription.company
        company_users = User.objects.filter(userprofile__company=company)
        
        for user in company_users:
            user_role = getattr(user.userprofile.role, 'name', 'None') if hasattr(user, 'userprofile') and user.userprofile.role else 'None'
            print(f"\nTesting User: {user.username} (Role: {user_role})")
            
            # Test the payment modal logic
            should_show = should_show_payment_modal(user)
            print(f"Should show payment modal: {should_show}")
            
            # Expected behavior:
            # - If trial is active: should NOT show modal
            # - If trial is expired: should SHOW modal
            expected_show = not subscription.is_trial_active
            print(f"Expected to show modal: {expected_show}")
            
            if should_show == expected_show:
                print("✅ PASS: Payment modal logic is correct")
            else:
                print("❌ FAIL: Payment modal logic is incorrect")
    
    print("\n=== Test Summary ===")
    
    # Test with a mock expired trial
    print("\n--- Testing Expired Trial Scenario ---")
    active_trial = trial_subscriptions.first()
    if active_trial:
        # Temporarily set trial_end_date to past to simulate expired trial
        original_end_date = active_trial.trial_end_date
        active_trial.trial_end_date = timezone.now() - timezone.timedelta(days=1)
        active_trial.save()
        
        print(f"Set trial end date to past: {active_trial.trial_end_date}")
        print(f"Is Trial Active: {active_trial.is_trial_active}")
        
        # Test with expired trial
        company_users = User.objects.filter(userprofile__company=active_trial.company)
        for user in company_users[:1]:  # Test first user
            should_show = should_show_payment_modal(user)
            print(f"User: {user.username}")
            print(f"Should show payment modal (expired trial): {should_show}")
            
            if should_show:
                print("✅ PASS: Payment modal shows for expired trial")
            else:
                print("❌ FAIL: Payment modal should show for expired trial")
        
        # Restore original trial_end_date
        active_trial.trial_end_date = original_end_date
        active_trial.save()
        print(f"Restored trial end date: {active_trial.trial_end_date}")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    test_payment_modal_fix()
