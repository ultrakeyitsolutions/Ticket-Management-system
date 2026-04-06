#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from superadmin.models import Payment
from django.db.models import Sum

print("=== Payment Analysis ===")
print(f"Total payments: {Payment.objects.count()}")

print("\nPayment status breakdown:")
for status in ['pending', 'completed', 'failed', 'refunded', 'cancelled']:
    count = Payment.objects.filter(status=status).count()
    total = Payment.objects.filter(status=status).aggregate(total=Sum('amount'))['total'] or 0
    print(f"{status}: {count} payments, total: ${total}")

print("\nCompleted payments (for revenue):")
completed_payments = Payment.objects.filter(status='completed')
if completed_payments.exists():
    total_revenue = completed_payments.aggregate(total=Sum('amount'))['total'] or 0
    print(f"Revenue from completed payments: ${total_revenue}")
    
    print("\nSample completed payments:")
    for payment in completed_payments[:5]:
        print(f"ID: {payment.id}, Amount: ${payment.amount}, Date: {payment.payment_date}")
else:
    print("No completed payments found")

print("\nAll recent payments:")
for payment in Payment.objects.all()[:5]:
    print(f"ID: {payment.id}, Amount: ${payment.amount}, Status: {payment.status}, Date: {payment.payment_date}")
