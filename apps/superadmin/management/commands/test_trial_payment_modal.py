from django.core.management.base import BaseCommand
from django.utils import timezone
from superadmin.models import Subscription
from superadmin.views import should_show_payment_modal
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Test payment modal fix for trial users'

    def handle(self, *args, **options):
        self.stdout.write("=== Testing Payment Modal Fix for Trial Users ===")
        
        # Get current trial subscriptions
        trial_subscriptions = Subscription.objects.filter(status='trial')
        self.stdout.write(f"Found {trial_subscriptions.count()} trial subscriptions")
        
        for subscription in trial_subscriptions:
            self.stdout.write(f"\n--- Testing Subscription {subscription.id} ---")
            self.stdout.write(f"Status: {subscription.status}")
            self.stdout.write(f"End Date: {subscription.end_date}")
            self.stdout.write(f"Trial End Date: {subscription.trial_end_date}")
            self.stdout.write(f"Is Trial Active: {subscription.is_trial_active}")
            self.stdout.write(f"Trial Days Remaining: {subscription.trial_days_remaining}")
            
            # Get users for this company
            company = subscription.company
            company_users = User.objects.filter(userprofile__in=company.users.all())
            
            for user in company_users:
                user_role = getattr(user.userprofile.role, 'name', 'None') if hasattr(user, 'userprofile') and user.userprofile.role else 'None'
                self.stdout.write(f"\nTesting User: {user.username} (Role: {user_role})")
                
                # Test the payment modal logic
                should_show = should_show_payment_modal(user)
                self.stdout.write(f"Should show payment modal: {should_show}")
                
                # Expected behavior:
                # - If trial is active: should NOT show modal
                # - If trial is expired: should SHOW modal
                expected_show = not subscription.is_trial_active
                self.stdout.write(f"Expected to show modal: {expected_show}")
                
                if should_show == expected_show:
                    self.stdout.write("✅ PASS: Payment modal logic is correct")
                else:
                    self.stdout.write("❌ FAIL: Payment modal logic is incorrect")
        
        self.stdout.write("\n=== Test Summary ===")
        
        # Test with a mock expired trial
        self.stdout.write("\n--- Testing Expired Trial Scenario ---")
        active_trial = trial_subscriptions.first()
        if active_trial:
            # Temporarily set trial_end_date to past to simulate expired trial
            original_end_date = active_trial.trial_end_date
            active_trial.trial_end_date = timezone.now() - timezone.timedelta(days=1)
            active_trial.save()
            
            self.stdout.write(f"Set trial end date to past: {active_trial.trial_end_date}")
            self.stdout.write(f"Is Trial Active: {active_trial.is_trial_active}")
            
            # Test with expired trial
            company_users = User.objects.filter(userprofile__in=active_trial.company.users.all())
            for user in company_users[:1]:  # Test first user
                should_show = should_show_payment_modal(user)
                self.stdout.write(f"User: {user.username}")
                self.stdout.write(f"Should show payment modal (expired trial): {should_show}")
                
                if should_show:
                    self.stdout.write("✅ PASS: Payment modal shows for expired trial")
                else:
                    self.stdout.write("❌ FAIL: Payment modal should show for expired trial")
            
            # Restore original trial_end_date
            active_trial.trial_end_date = original_end_date
            active_trial.save()
            self.stdout.write(f"Restored trial end date: {active_trial.trial_end_date}")
        
        self.stdout.write("\n=== Test Complete ===")
