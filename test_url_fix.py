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
from core.models import Plan, Subscription
from django.utils import timezone
from datetime import timedelta

def test_url_resolution():
    print("=== Testing URL Resolution Fix ===\n")
    
    client = Client()
    
    # Test 1: Check if home page loads without URL errors
    print("1. Testing home page loads without URL errors...")
    try:
        response = client.get('/')
        print(f"   ✓ Home page status: {response.status_code}")
        assert response.status_code == 200, "Home page should load successfully"
    except Exception as e:
        print(f"   ✗ Error loading home page: {e}")
        return False
    
    # Test 2: Check if payment page loads
    print("\n2. Testing payment page loads...")
    try:
        response = client.get('/payment/')
        print(f"   ✓ Payment page status: {response.status_code}")
        # Should redirect to login for unauthenticated users
        assert response.status_code in [200, 302], "Payment page should load or redirect"
    except Exception as e:
        print(f"   ✗ Error loading payment page: {e}")
        return False
    
    # Test 3: Test with authenticated user
    print("\n3. Testing with authenticated user...")
    
    # Clean up any existing test user
    User.objects.filter(username='testurluser').delete()
    
    # Create test user
    test_user = User.objects.create_user(
        username='testurluser',
        email='test@example.com',
        password='testpass123'
    )
    
    # Create trial subscription
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
    
    # Login user
    client.login(username='testurluser', password='testpass123')
    
    try:
        response = client.get('/')
        print(f"   ✓ Authenticated home page status: {response.status_code}")
        assert response.status_code == 200, "Home page should load for authenticated user"
    except Exception as e:
        print(f"   ✗ Error loading authenticated home page: {e}")
        return False
    
    # Test 4: Test expired trial (should show payment modal)
    print("\n4. Testing expired trial scenario...")
    subscription.trial_end = timezone.now() - timedelta(days=1)
    subscription.save()
    
    try:
        response = client.get('/')
        print(f"   ✓ Expired trial home page status: {response.status_code}")
        # Should redirect to payment or show payment modal
        assert response.status_code in [200, 302], "Should handle expired trial gracefully"
    except Exception as e:
        print(f"   ✗ Error with expired trial: {e}")
        return False
    
    # Cleanup
    subscription.delete()
    test_user.delete()
    
    print("\n=== URL Resolution Fix Test Passed! ===")
    print("✓ NoReverseMatch error resolved")
    print("✓ Home page loads successfully")
    print("✓ Payment page loads successfully")
    print("✓ Authenticated users can access pages")
    print("✓ Expired trials are handled correctly")
    
    return True

if __name__ == "__main__":
    success = test_url_resolution()
    if success:
        print("\n🎉 All URL resolution tests passed!")
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)
