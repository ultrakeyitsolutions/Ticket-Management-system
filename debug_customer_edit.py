#!/usr/bin/env python
"""
Debug script to test the customer edit API endpoint
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from apps.users.views import UserDetailView, _is_admin
from django.test import RequestFactory
from rest_framework.test import APIRequestFactory
from rest_framework.request import Request

def test_customer_edit_api():
    print("=== Testing Customer Edit API ===")
    
    # Create a mock request
    factory = APIRequestFactory()
    
    # Get a sample user (customer)
    try:
        customer = User.objects.filter(is_staff=False).first()
        if not customer:
            print("No customer found in database")
            return
            
        print(f"Testing with customer: {customer.username}")
        print(f"Customer ID: {customer.id}")
        print(f"Customer first_name: '{customer.first_name}'")
        print(f"Customer last_name: '{customer.last_name}'")
        print(f"Customer email: '{customer.email}'")
        
        # Create admin user for testing
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            print("No admin user found for testing")
            return
            
        # Create request
        request = factory.get(f'/api/users/{customer.id}/')
        request.user = admin_user
        
        # Create DRF request
        drf_request = Request(request)
        
        # Test the view
        view = UserDetailView()
        response = view.get(drf_request, customer.id)
        
        print(f"\nAPI Response Status: {response.status_code}")
        print(f"API Response Data: {response.data}")
        
        # Check if first_name and last_name are in response
        data = response.data
        print(f"\nField Check:")
        print(f"  - first_name in response: {'first_name' in data}")
        print(f"  - last_name in response: {'last_name' in data}")
        print(f"  - first_name value: '{data.get('first_name', 'NOT FOUND')}'")
        print(f"  - last_name value: '{data.get('last_name', 'NOT FOUND')}'")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_customer_edit_api()
