#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Setup Django
django.setup()

from core.models import Plan

def check_and_create_plans():
    print("Checking existing plans...")
    plans = Plan.objects.all()
    
    if plans.exists():
        print(f"Found {plans.count()} existing plans:")
        for plan in plans:
            print(f"  - {plan.name}: Trial Days = {plan.trial_days}, Status = {plan.status}")
    else:
        print("No plans found. Creating default plans...")
        
        # Create a Basic plan with 7-day trial
        basic_plan = Plan.objects.create(
            name="Basic",
            slug="basic",
            description="Perfect for getting started",
            plan_type="basic",
            price_monthly=9.99,
            trial_days=7,
            status="active",
            sort_order=1,
            features={
                "Basic Support": True,
                "Email Notifications": True,
                "10 Tickets/month": True,
                "1 Agent": True
            }
        )
        print(f"Created Basic plan with {basic_plan.trial_days}-day trial")
        
        # Create a Standard plan with 7-day trial
        standard_plan = Plan.objects.create(
            name="Standard",
            slug="standard",
            description="Great for growing teams",
            plan_type="standard",
            price_monthly=29.99,
            trial_days=7,
            status="active",
            sort_order=2,
            features={
                "Priority Support": True,
                "Email & SMS Notifications": True,
                "100 Tickets/month": True,
                "5 Agents": True,
                "Basic Analytics": True
            }
        )
        print(f"Created Standard plan with {standard_plan.trial_days}-day trial")
        
        # Create a Premium plan with 7-day trial
        premium_plan = Plan.objects.create(
            name="Premium",
            slug="premium",
            description="For large organizations",
            plan_type="premium",
            price_monthly=99.99,
            trial_days=7,
            status="active",
            sort_order=3,
            is_popular=True,
            features={
                "24/7 Phone Support": True,
                "All Notifications": True,
                "Unlimited Tickets": True,
                "Unlimited Agents": True,
                "Advanced Analytics": True,
                "Custom Integrations": True
            }
        )
        print(f"Created Premium plan with {premium_plan.trial_days}-day trial")

if __name__ == "__main__":
    check_and_create_plans()
