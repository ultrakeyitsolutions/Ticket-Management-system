from django.core.management.base import BaseCommand
from django.utils import timezone
from superadmin.models import Subscription
from datetime import timedelta

class Command(BaseCommand):
    help = 'Fix trial subscriptions that are missing trial_end_date field'

    def handle(self, *args, **options):
        self.stdout.write("=== Fixing Trial Subscriptions ===")
        
        # Find all trial subscriptions that don't have trial_end_date set
        trial_subs_missing_end_date = Subscription.objects.filter(
            status='trial',
            trial_end_date__isnull=True
        )
        
        self.stdout.write(f"Found {trial_subs_missing_end_date.count()} trial subscriptions missing trial_end_date")
        
        fixed_count = 0
        for subscription in trial_subs_missing_end_date:
            if subscription.end_date:
                # Set trial_end_date to end_date at 23:59:59
                trial_end_datetime = timezone.make_aware(
                    timezone.datetime.combine(
                        subscription.end_date, 
                        timezone.datetime.min.time()
                    )
                ) + timedelta(days=1) - timedelta(seconds=1)
                
                subscription.trial_end_date = trial_end_datetime
                subscription.save()
                
                self.stdout.write(f"Fixed subscription {subscription.id}: trial_end_date set to {trial_end_datetime}")
                fixed_count += 1
            else:
                self.stdout.write(f"Warning: Subscription {subscription.id} has no end_date, cannot fix")
        
        self.stdout.write(f"\nFixed {fixed_count} trial subscriptions")
        
        # Verify the fix
        self.stdout.write("\n=== Verification ===")
        active_trials = Subscription.objects.filter(
            status='trial',
            trial_end_date__isnull=False
        )
        
        self.stdout.write(f"Total trial subscriptions with trial_end_date: {active_trials.count()}")
        
        for subscription in active_trials[:5]:  # Show first 5
            is_active = subscription.is_trial_active
            days_remaining = subscription.trial_days_remaining
            self.stdout.write(f"Subscription {subscription.id}: Active={is_active}, Days remaining={days_remaining}")
        
        self.stdout.write("\n=== Fix Complete ===")
