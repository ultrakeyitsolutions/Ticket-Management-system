#!/usr/bin/env python
"""
Debug database to understand why company creation is failing
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from superadmin.models import Company
from users.models import UserProfile

def debug_database():
    """Debug database state"""
    
    print("=== DATABASE DEBUG INVESTIGATION ===")
    
    # Check recent companies
    print("\n📊 RECENT COMPANIES (Last 10):")
    recent_companies = Company.objects.all().order_by('-id')[:10]
    for company in recent_companies:
        print(f"  ID: {company.id:3d} | Name: {company.name:30s} | Email: {company.email:30s}")
    
    # Check recent users
    print("\n👤 RECENT USERS (Last 10):")
    recent_users = User.objects.all().order_by('-id')[:10]
    for user in recent_users:
        print(f"  ID: {user.id:3d} | Username: {user.username:30s} | Email: {user.email:30s}")
    
    # Check for specific problematic emails
    problematic_emails = ['sathhhh@gmail.com', 'hello2@gmail.com', 'newtest@gmail.com']
    
    print("\n🔍 CHECKING PROBLEMATIC EMAILS:")
    for email in problematic_emails:
        print(f"\n  Email: {email}")
        
        # Check Company table
        company_count = Company.objects.filter(email=email).count()
        print(f"    Company count: {company_count}")
        if company_count > 0:
            companies = Company.objects.filter(email=email)
            for company in companies:
                print(f"      - Company ID: {company.id}, Name: {company.name}")
        
        # Check User table
        user_count = User.objects.filter(email=email).count()
        print(f"    User count: {user_count}")
        if user_count > 0:
            users = User.objects.filter(email=email)
            for user in users:
                print(f"      - User ID: {user.id}, Username: {user.username}")
    
    # Check database constraints
    print("\n🔧 DATABASE CONSTRAINTS:")
    print("  Company.email has UNIQUE constraint")
    print("  User.email has UNIQUE constraint")
    print("  Both tables cannot have duplicate emails")
    
    # Test what happens when we try to insert
    print("\n🧪 TEST INSERTION:")
    test_email = 'newtest123@company.com'
    test_name = 'Test Company DB'
    
    print(f"  Testing with: {test_email}")
    
    # Check if exists
    company_exists = Company.objects.filter(email=test_email).exists()
    user_exists = User.objects.filter(email=test_email).exists()
    
    print(f"  Company exists: {company_exists}")
    print(f"  User exists: {user_exists}")
    
    if not company_exists and not user_exists:
        print("  ✅ This email should work for company creation")
        
        # Try to create a test company
        try:
            from django.contrib.auth.hashers import make_password
            test_company = Company.objects.create(
                name=test_name,
                email=test_email,
                phone='1234567890',
                address='Test Address',
                password=make_password('test123'),
                subscription_status='active',
                is_active=True
            )
            print(f"  ✅ Test company created successfully: ID {test_company.id}")
            
            # Clean up
            test_company.delete()
            print(f"  🧹 Test company cleaned up")
            
        except Exception as e:
            print(f"  ❌ Error creating test company: {e}")
    else:
        print("  ❌ This email already exists")
    
    print("\n💡 RECOMMENDATIONS:")
    print("1. Always use unique emails that don't exist in either table")
    print("2. Check both Company and User tables before creating")
    print("3. Use the validation system to prevent duplicates")
    print("4. If error persists, there might be a race condition")

if __name__ == '__main__':
    debug_database()
