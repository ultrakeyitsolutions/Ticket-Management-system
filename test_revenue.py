#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from superadmin.models import Plan, Payment, Subscription
from django.db.models import Sum

print("=== Revenue by Plan Analysis ===")
plans = Plan.objects.filter(is_active=True, status='active')

print("\nRevenue by plan (INR):")
total_revenue_by_plan = 0

for plan in plans:
    # Calculate revenue from completed payments for this plan
    plan_revenue_usd = Payment.objects.filter(
        subscription__plan=plan,
        status='completed'
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Convert to INR
    plan_revenue_inr = plan_revenue_usd * 83
    total_revenue_by_plan += plan_revenue_inr
    
    print(f"{plan.name}: ₹{plan_revenue_inr:,.2f}")

print(f"\nTotal revenue by plans: ₹{total_revenue_by_plan:,.2f}")

# Verify against total revenue
total_all_revenue = Payment.objects.filter(status='completed').aggregate(total=Sum('amount'))['total'] or 0
total_all_revenue_inr = total_all_revenue * 83
print(f"Total revenue all payments: ₹{total_all_revenue_inr:,.2f}")

print(f"\nData for chart:")
print(f"Data: {[float(Payment.objects.filter(subscription__plan=plan, status='completed').aggregate(total=Sum('amount'))['total'] or 0 * 83) for plan in plans]}")
print(f"Labels: {[plan.name for plan in plans]}")
