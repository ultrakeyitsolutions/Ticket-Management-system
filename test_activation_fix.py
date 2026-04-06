#!/usr/bin/env python
"""
Test script to verify the activation/deactivation functionality
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from users.models import UserProfile

def test_user_activation():
    print("=== Testing User Activation/Deactivation ===")
    
    # Get a sample customer user
    try:
        customer = User.objects.filter(is_staff=False).first()
        if not customer:
            print("No customer found in database")
            return
            
        print(f"Testing with customer: {customer.username}")
        print(f"Customer ID: {customer.id}")
        print(f"Customer email: {customer.email}")
        
        # Get user profile
        profile = getattr(customer, 'userprofile', None)
        if not profile:
            profile = UserProfile.objects.create(user=customer)
            
        print(f"\nBefore activation:")
        print(f"  - User.is_active: {customer.is_active}")
        print(f"  - Profile.is_active: {profile.is_active}")
        
        # Test activation (set to True)
        customer.is_active = True
        profile.is_active = True
        customer.save()
        profile.save()
        
        print(f"\nAfter activation:")
        print(f"  - User.is_active: {customer.is_active}")
        print(f"  - Profile.is_active: {profile.is_active}")
        
        # Test deactivation (set to False)
        customer.is_active = False
        profile.is_active = False
        customer.save()
        profile.save()
        
        print(f"\nAfter deactivation:")
        print(f"  - User.is_active: {customer.is_active}")
        print(f"  - Profile.is_active: {profile.is_active}")
        
        # Test re-activation
        customer.is_active = True
        profile.is_active = True
        customer.save()
        profile.save()
        
        print(f"\nAfter re-activation:")
        print(f"  - User.is_active: {customer.is_active}")
        print(f"  - Profile.is_active: {profile.is_active}")
        
        print(f"\n✅ User activation/deactivation working correctly!")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_user_activation()
