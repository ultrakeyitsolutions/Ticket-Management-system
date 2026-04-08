#!/usr/bin/env python
"""
Check FAQ data in the database
"""
import os
import sys
import django

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

try:
    from dashboards.models import Faq
    
    print(f"FAQ count: {Faq.objects.count()}")
    
    if Faq.objects.exists():
        print("\nFirst 5 FAQs:")
        for faq in Faq.objects.all()[:5]:
            print(f"- {faq.question} (Category: {faq.category or 'None'})")
    else:
        print("No FAQs found in database.")
        
except Exception as e:
    print(f"Error checking FAQ data: {e}")
    
    # Try alternative import
    try:
        from apps.dashboards.models import Faq
        print(f"FAQ count: {Faq.objects.count()}")
        
        if Faq.objects.exists():
            print("\nFirst 5 FAQs:")
            for faq in Faq.objects.all()[:5]:
                print(f"- {faq.question} (Category: {faq.category or 'None'})")
        else:
            print("No FAQs found in database.")
    except Exception as e2:
        print(f"Alternative import also failed: {e2}")
