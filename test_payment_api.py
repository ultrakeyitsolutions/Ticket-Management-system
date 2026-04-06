#!/usr/bin/env python
import os
import sys
import django

# Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Setup Django
django.setup()

from django.test import Client, RequestFactory
from django.contrib.auth.models import User
from core.models import Subscription
from core.views import check_payment_status

def test_payment_api():
    print("=== Testing Payment Status API ===\n")
    
    # Get the user
    try:
        user = User.objects.get(username='adhi12')
        print(f"✓ Testing for user: {user.username}")
    except User.DoesNotExist:
        print("✗ User 'adhi12' not found")
        return
    
    # Test 1: Using Django test client
    print("\n1. Testing with Test Client...")
    client = Client()
    client.force_login(user)
    
    try:
        response = client.get('/api/payment-status/')
        print(f"   Status code: {response.status_code}")
        print(f"   Response content: {response.json()}")
        
        data = response.json()
        needs_payment = data.get('needs_payment', False)
        print(f"   needs_payment: {needs_payment}")
        
        if needs_payment:
            print("   ⚠️  API says payment needed - modal will show")
        else:
            print("   ✅ API says no payment needed - modal should not show")
            
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Test 2: Using direct view function
    print("\n2. Testing with Direct View Function...")
    factory = RequestFactory()
    request = factory.get('/api/payment-status/')
    request.user = user
    
    # Get subscription (simulate middleware)
    subscription = Subscription.objects.filter(user=user).first()
    if subscription:
        request.subscription = subscription
        subscription.update_expired_trial()
        request.needs_payment = subscription.needs_payment()
        request.is_paid_user = subscription.is_paid()
    
    try:
        response = check_payment_status(request)
        print(f"   Status code: {response.status_code}")
        print(f"   Response content: {response.json()}")
        
        data = response.json()
        needs_payment = data.get('needs_payment', False)
        print(f"   needs_payment: {needs_payment}")
        
        if needs_payment:
            print("   ⚠️  Direct view says payment needed")
        else:
            print("   ✅ Direct view says no payment needed")
            
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Test 3: Check subscription directly
    print("\n3. Direct Subscription Check...")
    subscription = Subscription.objects.filter(user=user).first()
    if subscription:
        print(f"   Subscription status: {subscription.status}")
        print(f"   is_active(): {subscription.is_active()}")
        print(f"   is_trial_active(): {subscription.is_trial_active()}")
        print(f"   needs_payment(): {subscription.needs_payment()}")
        
        # Check what the API should return
        expected_needs_payment = subscription.needs_payment()
        print(f"   Expected needs_payment: {expected_needs_payment}")

if __name__ == "__main__":
    test_payment_api()
