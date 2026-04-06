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
from django.template.loader import render_to_string
from django.http import HttpRequest

def test_frontend_debug():
    print("=== Testing Frontend Template Context ===\n")
    
    # Get the user
    try:
        user = User.objects.get(username='adhi12')
        print(f"✓ Testing for user: {user.username}")
    except User.DoesNotExist:
        print("✗ User 'adhi12' not found")
        return
    
    # Create a mock request
    request = HttpRequest()
    request.user = user
    request.path = '/'
    
    # Get subscription (simulate middleware)
    from core.models import Subscription
    subscription = Subscription.objects.filter(user=user).first()
    if subscription:
        request.subscription = subscription
        subscription.update_expired_trial()
        request.needs_payment = subscription.needs_payment()
        request.is_paid_user = subscription.is_paid()
    
    print(f"\n--- Request Context ---")
    print(f"  User authenticated: {user.is_authenticated}")
    print(f"  Request path: {request.path}")
    print(f"  Needs payment: {getattr(request, 'needs_payment', 'Not set')}")
    print(f"  Is paid user: {getattr(request, 'is_paid_user', 'Not set')}")
    
    # Test template rendering
    print(f"\n--- Template JavaScript ---")
    
    # Check if the JavaScript condition should run
    should_check = user.is_authenticated and request.path != '/payment/'
    print(f"  Should check payment status: {should_check}")
    
    if should_check:
        print("  ✅ JavaScript will call checkPaymentStatus()")
    else:
        print("  ❌ JavaScript will NOT call checkPaymentStatus()")
    
    # Test the actual API endpoint that JavaScript calls
    print(f"\n--- API Endpoint Test ---")
    client = Client()
    client.force_login(user)
    
    try:
        response = client.get('/api/payment-status/')
        data = response.json()
        print(f"  API Response: {data}")
        print(f"  needs_payment from API: {data.get('needs_payment')}")
        
        if data.get('needs_payment'):
            print("  ⚠️  Frontend WILL show payment modal")
        else:
            print("  ✅ Frontend should NOT show payment modal")
            
    except Exception as e:
        print(f"  ✗ API Error: {e}")
    
    # Check if there might be any JavaScript errors
    print(f"\n--- Potential Issues ---")
    print("1. Check browser console for JavaScript errors")
    print("2. Check if the payment modal is being shown by other JavaScript")
    print("3. Check if there are multiple modals conflicting")
    print("4. Check browser cache (try hard refresh: Ctrl+F5)")
    
    # Create a simple HTML test to verify
    print(f"\n--- Creating Test Page ---")
    context = {
        'user': user,
        'request': request,
        'needs_payment': getattr(request, 'needs_payment', False),
        'is_paid_user': getattr(request, 'is_paid_user', False),
    }
    
    # Add subscription context
    if subscription:
        context.update({
            'subscription': subscription,
            'is_trial_active': subscription.is_trial_active(),
            'trial_days_remaining': subscription.get_trial_days_remaining(),
        })
    
    print(f"  Template context variables:")
    for key, value in context.items():
        if key not in ['request']:
            print(f"    {key}: {value}")

if __name__ == "__main__":
    test_frontend_debug()
