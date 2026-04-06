#!/usr/bin/env python
"""
Test script to verify notification functionality
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from users.models import UserProfile
from core.notifications import NotificationService

def test_notification_functionality():
    """Test notification functionality"""
    print("Testing notification functionality...")
    
    try:
        # Get current user
        user = User.objects.first()
        if not user:
            print("❌ No users found in database.")
            return
            
        print(f"👤 Testing with user: {user.username}")
        print(f"📧 Email: {user.email}")
        
        # Get or create user profile
        profile, created = UserProfile.objects.get_or_create(user=user)
        
        if created:
            print("📝 Created new user profile")
        
        # Test notification preferences
        print(f"\n🔔 Testing notification preferences...")
        
        # Enable all notifications
        profile.email_notifications = True
        profile.desktop_notifications = True
        profile.allow_dm_from_non_contacts = True
        profile.save()
        
        print(f"✅ Email notifications: {profile.email_notifications}")
        print(f"✅ Push notifications: {profile.desktop_notifications}")
        print(f"✅ Marketing emails: {profile.allow_dm_from_non_contacts}")
        
        # Test email notification
        print(f"\n📧 Testing email notification...")
        
        try:
            result = NotificationService.send_email_notification(
                user=user,
                subject="Test Email Notification",
                message="This is a test email notification from TicketHub."
            )
            if result:
                print(f"✅ Email notification sent successfully!")
            else:
                print(f"❌ Email notification failed or disabled")
        except Exception as e:
            print(f"❌ Email notification error: {e}")
        
        # Test push notification
        print(f"\n📱 Testing push notification...")
        
        try:
            result = NotificationService.send_push_notification(
                user=user,
                title="Test Push Notification",
                message="This is a test push notification from TicketHub."
            )
            if result:
                print(f"✅ Push notification sent successfully!")
            else:
                print(f"❌ Push notification failed or disabled")
        except Exception as e:
            print(f"❌ Push notification error: {e}")
        
        # Test marketing email
        print(f"\n📢 Testing marketing email...")
        
        try:
            result = NotificationService.send_marketing_email(
                user=user,
                subject="Test Marketing Campaign",
                message="This is a test marketing email from TicketHub."
            )
            if result:
                print(f"✅ Marketing email sent successfully!")
            else:
                print(f"❌ Marketing email failed or disabled")
        except Exception as e:
            print(f"❌ Marketing email error: {e}")
        
        # Test notification with disabled preferences
        print(f"\n🔕 Testing with disabled notifications...")
        
        # Disable all notifications
        profile.email_notifications = False
        profile.desktop_notifications = False
        profile.allow_dm_from_non_contacts = False
        profile.save()
        
        print(f"📧 Email notifications: {profile.email_notifications}")
        print(f"📱 Push notifications: {profile.desktop_notifications}")
        print(f"📢 Marketing emails: {profile.allow_dm_from_non_contacts}")
        
        # Test with disabled notifications
        email_result = NotificationService.send_email_notification(
            user=user,
            subject="Test (Should Fail)",
            message="This should not be sent."
        )
        
        if not email_result:
            print(f"✅ Email notification correctly blocked")
        else:
            print(f"❌ Email notification should have been blocked")
        
        # Re-enable notifications
        profile.email_notifications = True
        profile.desktop_notifications = True
        profile.allow_dm_from_non_contacts = True
        profile.save()
        
        # Test specific notification types
        print(f"\n🎫 Testing ticket notifications...")
        
        # Create a mock ticket for testing
        from tickets.models import Ticket
        
        # Create a test ticket
        ticket, created = Ticket.objects.get_or_create(
            ticket_id="TEST-001",
            defaults={
                'title': "Test Ticket",
                'description': "This is a test ticket for notification testing.",
                'created_by': user,
                'category': 'Technical',
                'priority': 'Medium',
                'status': 'Open'
            }
        )
        
        if created:
            print(f"📝 Created test ticket: {ticket.ticket_id}")
        else:
            print(f"📝 Using existing test ticket: {ticket.ticket_id}")
        
        # Test ticket created notification
        try:
            NotificationService.notify_ticket_created(ticket)
            print(f"✅ Ticket created notification sent")
        except Exception as e:
            print(f"❌ Ticket created notification error: {e}")
        
        # Test password change notification
        print(f"\n🔐 Testing password change notification...")
        
        try:
            NotificationService.send_password_change_notification(user)
            print(f"✅ Password change notification sent")
        except Exception as e:
            print(f"❌ Password change notification error: {e}")
        
        # Test 2FA enabled notification
        print(f"\n🔒 Testing 2FA enabled notification...")
        
        try:
            NotificationService.send_2fa_enabled_notification(user)
            print(f"✅ 2FA enabled notification sent")
        except Exception as e:
            print(f"❌ 2FA enabled notification error: {e}")
        
        print(f"\n🎉 Notification functionality test completed!")
        
    except Exception as e:
        print(f"❌ Error testing notification functionality: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_notification_functionality()
