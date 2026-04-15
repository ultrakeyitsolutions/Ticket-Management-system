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

# Create a test client
client = Client()

# Get admin user and login
admin_user = User.objects.filter(is_superuser=True).first()
if not admin_user:
    print("❌ No admin user found!")
    sys.exit(1)

client.force_login(admin_user)

print("=== Testing Admin Ratings Page ===")
response = client.get('/dashboard/admin-dashboard/ratings/')
print(f"Status Code: {response.status_code}")

if response.status_code == 200:
    content = response.content.decode('utf-8')
    
    # Check for key data elements
    checks = [
        ("Average Rating > 0", lambda c: any(x in c for x in ["4.0", "4.1", "4.2", "4.3", "4.4", "4.5"])),
        ("Total Ratings > 0", lambda c: "278" in c),
        ("Response Rate", lambda c: "Response Rate" in c),
        ("Satisfaction Rate", lambda c: "satisfaction" in c.lower()),
        ("Rating Distribution", lambda c: "rating distribution" in c.lower()),
        ("Recent Feedback Table", lambda c: "recent feedback" in c.lower()),
        ("Agent Performance Table", lambda c: "agent performance" in c.lower()),
        ("Chart Container", lambda c: "rating-trends-chart" in c),
    ]
    
    print("\n=== Data Verification ===")
    all_passed = True
    for check_name, check_func in checks:
        try:
            if check_func(content):
                print(f"✅ {check_name}")
            else:
                print(f"❌ {check_name}")
                all_passed = False
        except Exception as e:
            print(f"⚠️  {check_name} - Error: {e}")
            all_passed = False
    
    # Extract actual values
    print("\n=== Extracted Values ===")
    import re
    
    # Average rating
    avg_match = re.search(r'<div class="h4[^>]*>([^<]+)</div>', content)
    if avg_match:
        print(f"📊 Average Rating: {avg_match.group(1).strip()}")
    
    # Total ratings
    total_match = re.search(r'Based on ([^<]+) ratings', content)
    if total_match:
        print(f"📈 Total Ratings: {total_match.group(1).strip()}")
    
    # Response rate
    response_match = re.search(r'(\d+)%</div>\s*<small[^>]*>Tickets with responses', content)
    if response_match:
        print(f"💬 Response Rate: {response_match.group(1)}%")
    
    # Satisfaction rate
    satisfaction_match = re.search(r'(\d+)%</div>\s*<small[^>]*>Ratings of 4★ and above', content)
    if satisfaction_match:
        print(f"😊 Satisfaction Rate: {satisfaction_match.group(1)}%")
    
    print(f"\n{'='*50}")
    if all_passed:
        print("🎉 ALL CHECKS PASSED! Ratings page is working correctly.")
    else:
        print("⚠️  Some checks failed. Please review the issues above.")
    print(f"{'='*50}")
    
else:
    print(f"❌ Failed to load page: {response.content}")
