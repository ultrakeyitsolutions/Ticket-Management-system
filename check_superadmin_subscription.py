#!/usr/bin/env python
import os
import sys
import django

# Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Setup Django
django.setup()

from django.contrib.auth.models import User
from superadmin.models import Subscription as SuperadminSubscription, Company
from core.models import Subscription as CoreSubscription
from users.models import UserProfile
from django.utils import timezone

def check_subscription_models():
    print("=== Checking Both Subscription Models ===\n")
    
    # Get the user
    try:
        user = User.objects.get(username='adhi12')
        print(f"✓ Found user: {user.username}")
    except User.DoesNotExist:
        print("✗ User 'adhi12' not found")
        return
    
    # Check Core subscription (user-based)
    print("\n--- Core Subscription (user-based) ---")
    core_sub = CoreSubscription.objects.filter(user=user).first()
    if core_sub:
        print(f"✓ Found core subscription:")
        print(f"  Status: {core_sub.status}")
        print(f"  Plan: {core_sub.plan.name if core_sub.plan else 'No Plan'}")
        print(f"  Trial start: {core_sub.trial_start}")
        print(f"  Trial end: {core_sub.trial_end}")
        print(f"  is_active(): {core_sub.is_active()}")
        print(f"  is_trial_active(): {core_sub.is_trial_active()}")
        print(f"  needs_payment(): {core_sub.needs_payment()}")
    else:
        print("✗ No core subscription found")
    
    # Check Superadmin subscription (company-based)
    print("\n--- Superadmin Subscription (company-based) ---")
    
    # Get user's profile and company
    profile = getattr(user, 'userprofile', None)
    user_company = None
    
    if profile:
        user_company = Company.objects.filter(users=profile).first()
        if user_company:
            print(f"✓ Found company: {user_company.name}")
            
            # Check for active subscription
            active_sub = SuperadminSubscription.objects.filter(
                company=user_company,
                status='active'
            ).first()
            
            if active_sub:
                print(f"✓ Found active subscription:")
                print(f"  Status: {active_sub.status}")
                print(f"  Plan: {active_sub.plan.name if active_sub.plan else 'No Plan'}")
            else:
                print("✗ No active subscription found")
            
            # Check for trial subscription
            trial_sub = SuperadminSubscription.objects.filter(
                company=user_company,
                status='trial'
            ).first()
            
            if trial_sub:
                print(f"✓ Found trial subscription:")
                print(f"  Status: {trial_sub.status}")
                print(f"  Plan: {trial_sub.plan.name if trial_sub.plan else 'No Plan'}")
                print(f"  Trial end date: {trial_sub.trial_end_date}")
                
                if trial_sub.trial_end_date:
                    is_trial_valid = trial_sub.trial_end_date > timezone.now()
                    print(f"  Is trial valid: {is_trial_valid}")
                    if is_trial_valid:
                        print(f"  Days remaining: {(trial_sub.trial_end_date - timezone.now()).days}")
            else:
                print("✗ No trial subscription found")
            
            # Check all subscriptions for this company
            all_subs = SuperadminSubscription.objects.filter(company=user_company)
            print(f"\n✓ Total superadmin subscriptions for company: {all_subs.count()}")
            for sub in all_subs:
                print(f"  - {sub.status}: {sub.plan.name if sub.plan else 'No Plan'}")
                
        else:
            print("✗ No company found for user")
    else:
        print("✗ No user profile found")
    
    # Test the should_show_payment_modal function directly
    print(f"\n--- Testing should_show_payment_modal() ---")
    try:
        from superadmin.views import should_show_payment_modal
        should_show = should_show_payment_modal(user)
        print(f"should_show_payment_modal() returns: {should_show}")
        
        if should_show:
            print("⚠️  This function WILL show the payment modal")
        else:
            print("✅ This function will NOT show the payment modal")
            
    except Exception as e:
        print(f"✗ Error calling should_show_payment_modal(): {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_subscription_models()
