#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
# from apps.accounts.models import UserProfile, Role

# Create a test client
client = Client()

# Get or create admin user
try:
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        print("No admin user found!")
        sys.exit(1)
    
    # Log in as admin
    client.force_login(admin_user)
    
    # Test the ratings trends API
    print("=== Testing Ratings Trends API ===")
    response = client.get('/dashboard/admin-dashboard/api/ratings-trends/?period=week')
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        import json
        data = json.loads(response.content)
        print(f"Response Data: {data}")
    else:
        print(f"Response Content: {response.content}")
    
    # Test the ratings page
    print("\n=== Testing Ratings Page ===")
    response = client.get('/dashboard/admin-dashboard/ratings/')
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        # Check if template variables are in the response
        content = response.content.decode('utf-8')
        print(f"Content length: {len(content)}")
        print("=== Looking for template variables ===")
        
        # Check for specific template variable patterns
        patterns = [
            'ratings_admin_avg',
            'ratings_admin_total', 
            'ratings_admin_satisfaction_percent',
            'ratings_response_rate',
            'ratings_avg_response_hours',
            'ratings_distribution',
            'ratings_admin_recent'
        ]
        
        for pattern in patterns:
            if pattern in content:
                print(f"✓ Found {pattern}")
            else:
                print(f"✗ Missing {pattern}")
        
        # Look for actual data values vs defaults
        print("\n=== Checking for actual data ===")
        if '4.3' in content:  # We know avg is 4.38
            print("✓ Found actual average rating (4.3)")
        elif '0.0' in content:
            print("✗ Showing default average rating (0.0)")
            
        if '278' in content:  # We know total is 278
            print("✓ Found actual total ratings (278)")
        elif '"0"' in content or '0 ratings' in content:
            print("✗ Showing default total ratings (0)")
            
        # Show a snippet of the content around where ratings should be
        if 'Average Rating' in content:
            idx = content.find('Average Rating')
            snippet = content[max(0, idx-50):idx+300]
            print(f"\n=== Content around 'Average Rating' ===")
            print(snippet)
            
        # Look for the actual rendered values
        print("\n=== Looking for rendered values ===")
        import re
        
        # Look for the h4 element that should contain the average rating
        avg_rating_match = re.search(r'<div class="h4[^>]*>([^<]+)</div>', content)
        if avg_rating_match:
            print(f"Average rating found: '{avg_rating_match.group(1).strip()}'")
        
        # Look for "Based on X ratings" text
        total_match = re.search(r'Based on ([^<]+) ratings', content)
        if total_match:
            print(f"Total ratings found: '{total_match.group(1).strip()}'")
            
        # Check if Django template syntax is still present
        print("\n=== Checking for Django Template Syntax ===")
        if '{{' in content and '}}' in content:
            print("✗ Django template syntax found in output (not processed)")
            # Find examples
            import re
            template_vars = re.findall(r'\{\{[^}]+\}\}', content)
            print(f"Found {len(template_vars)} template variables: {template_vars[:5]}")
        else:
            print("✓ Django template syntax properly processed")
    else:
        print(f"Response Content: {response.content}")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
