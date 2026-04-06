#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from superadmin.models import Plan, Subscription

print("=== Revenue Breakdown Analysis ===")
print("Active plans:")
plans = Plan.objects.filter(is_active=True, status='active')
for plan in plans:
    print(f"Plan: {plan.name}")

print("\nPlan distribution (active subscriptions):")
for plan in plans:
    count = Subscription.objects.filter(plan=plan, status='active').count()
    print(f"{plan.name}: {count} active subscriptions")

print("\nPlan distribution data for chart:")
plan_distribution_data = []
plan_distribution_labels = []

for plan in plans:
    subscription_count = Subscription.objects.filter(
        plan=plan,
        status='active'
    ).count()
    plan_distribution_data.append(subscription_count)
    plan_distribution_labels.append(plan.name)

print(f"Data: {plan_distribution_data}")
print(f"Labels: {plan_distribution_labels}")
