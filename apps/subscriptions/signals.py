from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from superadmin.models import Plan, Company
from users.models import UserProfile
from .models import UserSubscription, SubscriptionHistory


@receiver(post_save, sender=User)
def create_user_subscription(sender, instance, created, **kwargs):
    """Automatically create free trial subscription for new users"""
    if created:
        try:
            # Get or create free trial plan
            free_trial_plan = Plan.objects.filter(name='Free Trial', is_active=True).first()
            
            if free_trial_plan:
                # Create or get company for user
                company_name = f"{instance.username}'s Company"
                company, created = Company.objects.get_or_create(
                    email=instance.email,
                    defaults={
                        'name': company_name,
                        'phone': '',
                        'plan': free_trial_plan,
                        'subscription_status': 'trial',
                        'subscription_start_date': timezone.now().date(),
                        'plan_expiry_date': (timezone.now() + timedelta(days=7)).date(),
                    }
                )
                
                if not created:
                    # Update existing company
                    company.plan = free_trial_plan
                    company.subscription_status = 'trial'
                    company.subscription_start_date = timezone.now().date()
                    company.plan_expiry_date = (timezone.now() + timedelta(days=7)).date()
                    company.save()
                
                # Update user profile with company
                try:
                    user_profile = instance.userprofile
                    user_profile.company = company
                    user_profile.save()
                except UserProfile.DoesNotExist:
                    # Create user profile if it doesn't exist
                    from users.models import Role
                    default_role = Role.objects.filter(name='User').first()
                    UserProfile.objects.create(
                        user=instance,
                        role=default_role,
                        company=company
                    )
                
                # Create subscription
                subscription = UserSubscription.objects.create(
                    user=instance,
                    company=company,
                    plan=free_trial_plan,
                    start_date=timezone.now(),
                    end_date=timezone.now() + timedelta(days=7),
                    trial_end_date=timezone.now() + timedelta(days=7),
                    status='trial'
                )
                
                # Create subscription history
                SubscriptionHistory.objects.create(
                    subscription=subscription,
                    action='trial_started',
                    new_plan=free_trial_plan,
                    description=f'Free trial started for {instance.username}'
                )
                
                print(f"Free trial subscription created for user: {instance.username}")
                
        except Exception as e:
            print(f"Error creating subscription for user {instance.username}: {str(e)}")


@receiver(post_save, sender=UserProfile)
def update_user_subscription(sender, instance, created, **kwargs):
    """Update subscription when user profile is created/updated"""
    if created and not instance.company:
        try:
            # Get free trial plan
            free_trial_plan = Plan.objects.filter(name='Free Trial', is_active=True).first()
            
            if free_trial_plan:
                # Create company for user
                company_name = f"{instance.user.username}'s Company"
                company, company_created = Company.objects.get_or_create(
                    email=instance.user.email,
                    defaults={
                        'name': company_name,
                        'phone': '',
                        'plan': free_trial_plan,
                        'subscription_status': 'trial',
                        'subscription_start_date': timezone.now().date(),
                        'plan_expiry_date': (timezone.now() + timedelta(days=7)).date(),
                    }
                )
                
                # Update user profile with company
                instance.company = company
                instance.save()
                
                print(f"Company created and assigned to user profile: {instance.user.username}")
                
        except Exception as e:
            print(f"Error updating subscription for user profile {instance.user.username}: {str(e)}")
