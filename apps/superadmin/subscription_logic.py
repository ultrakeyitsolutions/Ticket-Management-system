"""
Subscription Business Logic
Handles free trials, plan upgrades, and subscription management
"""

from django.utils import timezone
from datetime import timedelta
from django.db import transaction
from django.contrib import messages
from .models import Plan, Company, Subscription, Payment, SubscriptionMetrics


class SubscriptionManager:
    """Manages subscription operations and business logic"""
    
    @staticmethod
    def create_free_trial_subscription(company, plan=None):
        """
        Create a 7-day free trial subscription for a company
        If no plan specified, uses the Free Trial plan
        """
        try:
            with transaction.atomic():
                # Get Free Trial plan if not specified
                if not plan:
                    plan = Plan.objects.get(name='Free Trial')
                
                # Check if company already has an active trial
                existing_trial = Subscription.objects.filter(
                    company=company,
                    status='trial'
                ).first()
                
                if existing_trial:
                    return existing_trial
                
                # Create new trial subscription
                trial_end_date = timezone.now().date() + timedelta(days=7)
                
                subscription = Subscription.objects.create(
                    company=company,
                    plan=plan,
                    status='trial',
                    start_date=timezone.now().date(),
                    end_date=trial_end_date,
                    created_at=timezone.now()
                )
                
                # Update company plan
                company.plan = plan
                company.plan_expiry_date = trial_end_date
                company.subscription_status = 'trial'
                company.subscription_start_date = timezone.now().date()
                company.save()
                
                # Create metrics record
                SubscriptionMetrics.objects.create(
                    plan=plan,
                    date=timezone.now().date(),
                    new_subscriptions=1,
                    active_subscriptions=1,
                    revenue=0
                )
                
                return subscription
                
        except Exception as e:
            raise Exception(f"Error creating trial subscription: {str(e)}")
    
    @staticmethod
    def upgrade_from_trial(company, new_plan):
        """Upgrade from trial to paid plan"""
        try:
            with transaction.atomic():
                # Get current trial subscription
                trial_sub = Subscription.objects.filter(
                    company=company,
                    status='trial'
                ).first()
                
                if not trial_sub:
                    raise Exception("No active trial subscription found")
                
                # Calculate subscription dates
                start_date = timezone.now().date()
                
                # Determine end date based on billing cycle
                if new_plan.billing_cycle == 'monthly':
                    end_date = start_date + timedelta(days=30)
                else:  # yearly
                    end_date = start_date + timedelta(days=365)
                
                # Create new paid subscription
                subscription = Subscription.objects.create(
                    company=company,
                    plan=new_plan,
                    status='active',
                    start_date=start_date,
                    end_date=end_date,
                    created_at=timezone.now()
                )
                
                # Update trial subscription
                trial_sub.status = 'upgraded'
                trial_sub.save()
                
                # Update company
                company.plan = new_plan
                company.plan_expiry_date = end_date
                company.subscription_status = 'active'
                company.subscription_start_date = start_date
                company.save()
                
                # Create payment record
                Payment.objects.create(
                    subscription=subscription,
                    amount=new_plan.price,
                    payment_method='system',
                    payment_date=timezone.now(),
                    status='completed'
                )
                
                # Update metrics
                SubscriptionMetrics.objects.create(
                    plan=new_plan,
                    date=timezone.now().date(),
                    new_subscriptions=1,
                    active_subscriptions=1,
                    revenue=new_plan.price
                )
                
                return subscription
                
        except Exception as e:
            raise Exception(f"Error upgrading from trial: {str(e)}")
    
    @staticmethod
    def renew_subscription(subscription):
        """Renew an existing subscription"""
        try:
            with transaction.atomic():
                plan = subscription.plan
                
                # Calculate new end date
                if plan.billing_cycle == 'monthly':
                    new_end_date = subscription.end_date + timedelta(days=30)
                else:  # yearly
                    new_end_date = subscription.end_date + timedelta(days=365)
                
                # Create new subscription record
                new_subscription = Subscription.objects.create(
                    company=subscription.company,
                    plan=plan,
                    status='active',
                    start_date=subscription.end_date + timedelta(days=1),
                    end_date=new_end_date,
                    created_at=timezone.now()
                )
                
                # Update old subscription
                subscription.status = 'renewed'
                subscription.save()
                
                # Update company
                company = subscription.company
                company.plan_expiry_date = new_end_date
                company.subscription_status = 'active'
                company.save()
                
                # Create payment record
                Payment.objects.create(
                    subscription=new_subscription,
                    amount=plan.price,
                    payment_method='system',
                    payment_date=timezone.now(),
                    status='completed'
                )
                
                # Update metrics
                SubscriptionMetrics.objects.create(
                    plan=plan,
                    date=timezone.now().date(),
                    new_subscriptions=0,  # Renewal, not new
                    active_subscriptions=1,
                    revenue=plan.price
                )
                
                return new_subscription
                
        except Exception as e:
            raise Exception(f"Error renewing subscription: {str(e)}")
    
    @staticmethod
    def change_plan(subscription, new_plan):
        """Change subscription to a different plan"""
        try:
            with transaction.atomic():
                old_plan = subscription.plan
                
                # Calculate prorated amount (simplified)
                days_remaining = (subscription.end_date - timezone.now().date()).days
                total_days = 30 if old_plan.billing_cycle == 'monthly' else 365
                
                prorated_amount = (new_plan.price - old_plan.price) * (days_remaining / total_days)
                
                # Create new subscription with new plan
                new_subscription = Subscription.objects.create(
                    company=subscription.company,
                    plan=new_plan,
                    status='active',
                    start_date=timezone.now().date(),
                    end_date=subscription.end_date,
                    created_at=timezone.now()
                )
                
                # Update old subscription
                subscription.status = 'changed'
                subscription.save()
                
                # Update company
                company = subscription.company
                company.plan = new_plan
                company.save()
                
                # Create payment record for plan change
                if prorated_amount > 0:
                    Payment.objects.create(
                        subscription=new_subscription,
                        amount=prorated_amount,
                        payment_method='system',
                        payment_date=timezone.now(),
                        status='completed',
                        payment_type='plan_change'
                    )
                
                # Update metrics
                SubscriptionMetrics.objects.create(
                    plan=new_plan,
                    date=timezone.now().date(),
                    new_subscriptions=0,
                    active_subscriptions=1,
                    revenue=prorated_amount if prorated_amount > 0 else 0
                )
                
                return new_subscription
                
        except Exception as e:
            raise Exception(f"Error changing plan: {str(e)}")
    
    @staticmethod
    def cancel_subscription(subscription, reason='user_request'):
        """Cancel a subscription"""
        try:
            with transaction.atomic():
                # Update subscription status
                subscription.status = 'cancelled'
                subscription.end_date = timezone.now().date()
                subscription.save()
                
                # Update company
                company = subscription.company
                company.subscription_status = 'cancelled'
                company.save()
                
                # Update metrics (decrement active count)
                SubscriptionMetrics.objects.create(
                    plan=subscription.plan,
                    date=timezone.now().date(),
                    new_subscriptions=0,
                    active_subscriptions=-1,  # Cancelled
                    revenue=0
                )
                
                return True
                
        except Exception as e:
            raise Exception(f"Error cancelling subscription: {str(e)}")
    
    @staticmethod
    def check_subscription_expiry():
        """Check and update expired subscriptions"""
        try:
            today = timezone.now().date()
            expired_subscriptions = Subscription.objects.filter(
                end_date__lt=today,
                status='active'
            )
            
            for subscription in expired_subscriptions:
                subscription.status = 'expired'
                subscription.save()
                
                # Update company status
                company = subscription.company
                company.subscription_status = 'expired'
                company.save()
                
                # Update metrics
                SubscriptionMetrics.objects.create(
                    plan=subscription.plan,
                    date=today,
                    new_subscriptions=0,
                    active_subscriptions=-1,
                    revenue=0
                )
            
            return len(expired_subscriptions)
            
        except Exception as e:
            raise Exception(f"Error checking subscription expiry: {str(e)}")
    
    @staticmethod
    def get_subscription_stats(plan_id=None, days=30):
        """Get subscription statistics"""
        try:
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=days)
            
            queryset = Subscription.objects.filter(created_at__date__gte=start_date)
            if plan_id:
                queryset = queryset.filter(plan_id=plan_id)
            
            stats = {
                'total_subscriptions': queryset.count(),
                'active_subscriptions': queryset.filter(status='active').count(),
                'trial_subscriptions': queryset.filter(status='trial').count(),
                'expired_subscriptions': queryset.filter(status='expired').count(),
                'cancelled_subscriptions': queryset.filter(status='cancelled').count(),
                'total_revenue': Payment.objects.filter(
                    subscription__in=queryset,
                    status='completed'
                ).aggregate(total=models.Sum('amount'))['total'] or 0
            }
            
            return stats
            
        except Exception as e:
            raise Exception(f"Error getting subscription stats: {str(e)}")


def handle_trial_expiry():
    """Handle trial expiry - convert to expired or upgrade"""
    try:
        today = timezone.now().date()
        expired_trials = Subscription.objects.filter(
            end_date__lt=today,
            status='trial'
        )
        
        for trial in expired_trials:
            trial.status = 'expired'
            trial.save()
            
            # Update company
            company = trial.company
            company.subscription_status = 'expired'
            company.save()
            
            # Update metrics
            SubscriptionMetrics.objects.create(
                plan=trial.plan,
                date=today,
                new_subscriptions=0,
                active_subscriptions=-1,
                revenue=0
            )
        
        return len(expired_trials)
        
    except Exception as e:
        raise Exception(f"Error handling trial expiry: {str(e)}")
