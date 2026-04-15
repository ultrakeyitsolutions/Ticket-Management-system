from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from superadmin.models import Plan, Company


class UserSubscription(models.Model):
    """Subscription model for managing user subscriptions"""
    
    STATUS_CHOICES = [
        ('trial', 'Trial'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
        ('pending', 'Pending Payment'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_subscriptions')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='company_subscriptions')
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name='plan_subscriptions')
    
    # Subscription dates
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    trial_end_date = models.DateTimeField(null=True, blank=True)
    
    # Status and payment
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='trial')
    is_active = models.BooleanField(default=True)
    auto_renew = models.BooleanField(default=True)
    
    # Payment details
    payment_id = models.CharField(max_length=100, null=True, blank=True)
    payment_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    payment_method = models.CharField(max_length=50, null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'subscriptions'
        
    def __str__(self):
        return f"{self.user.username} - {self.plan.name} ({self.status})"
    
    def is_trial_active(self):
        """Check if trial is still active"""
        if self.trial_end_date and self.status == 'trial':
            return timezone.now() < self.trial_end_date
        return False
    
    def trial_days_remaining(self):
        """Get remaining trial days"""
        if self.trial_end_date:
            remaining = self.trial_end_date - timezone.now()
            return max(0, remaining.days)
        return 0
    
    def is_subscription_active(self):
        """Check if subscription is active"""
        if self.status == 'active' and self.end_date:
            return timezone.now() < self.end_date
        return False
    
    def days_until_expiry(self):
        """Get days until subscription expires"""
        if self.end_date:
            remaining = self.end_date - timezone.now()
            return max(0, remaining.days)
        return 0
    
    def activate_trial(self, trial_days=7):
        """Activate trial subscription"""
        self.status = 'trial'
        self.start_date = timezone.now()
        self.trial_end_date = timezone.now() + timedelta(days=trial_days)
        self.end_date = self.trial_end_date
        self.save()
    
    def activate_subscription(self, payment_id=None, payment_amount=None):
        """Activate paid subscription"""
        self.status = 'active'
        self.start_date = timezone.now()
        
        # Calculate end date based on plan billing cycle
        if self.plan.billing_cycle == 'monthly':
            self.end_date = timezone.now() + timedelta(days=30)
        elif self.plan.billing_cycle == 'yearly':
            self.end_date = timezone.now() + timedelta(days=365)
        else:
            self.end_date = timezone.now() + timedelta(days=30)  # Default to monthly
        
        self.trial_end_date = None
        self.payment_id = payment_id
        self.payment_amount = payment_amount
        self.paid_at = timezone.now()
        self.save()
    
    def cancel_subscription(self):
        """Cancel subscription"""
        self.status = 'cancelled'
        self.auto_renew = False
        self.save()
    
    def expire_subscription(self):
        """Mark subscription as expired"""
        self.status = 'expired'
        self.is_active = False
        self.save()


class SubscriptionHistory(models.Model):
    """Track subscription changes and payments"""
    
    subscription = models.ForeignKey(UserSubscription, on_delete=models.CASCADE)
    action = models.CharField(max_length=50)  # 'trial_started', 'payment_received', 'plan_changed', 'cancelled'
    old_plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True, blank=True, related_name='old_plan_history')
    new_plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True, blank=True, related_name='new_plan_history')
    payment_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    payment_id = models.CharField(max_length=100, null=True, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        app_label = 'subscriptions'
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.subscription.user.username} - {self.action}"


class PaymentTransaction(models.Model):
    """Track payment transactions"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_transactions')
    subscription = models.ForeignKey(UserSubscription, on_delete=models.CASCADE)
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE)
    
    # Payment details
    payment_id = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='INR')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Gateway details
    gateway = models.CharField(max_length=50, default='razorpay')
    gateway_response = models.JSONField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        app_label = 'subscriptions'
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.user.username} - {self.amount} {self.currency} ({self.status})"
