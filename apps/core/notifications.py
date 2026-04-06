"""
Notification services for handling different types of notifications
"""
import logging
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from users.models import UserProfile

logger = logging.getLogger(__name__)

class NotificationService:
    """Service for handling various types of notifications"""
    
    @staticmethod
    def send_email_notification(user, subject, message, template=None, context=None):
        """
        Send email notification to user if they have enabled email notifications
        """
        try:
            # Get user profile to check email notification preference
            profile = getattr(user, 'userprofile', None)
            if not profile or not profile.email_notifications:
                logger.info(f"Email notifications disabled for user {user.username}")
                return False
            
            # Prepare email content
            if template and context:
                html_message = render_to_string(template, context)
                plain_message = strip_tags(html_message)
            else:
                plain_message = message
                html_message = None
            
            # Send email
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False
            )
            
            logger.info(f"Email notification sent to {user.email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email notification to {user.email}: {str(e)}")
            return False
    
    @staticmethod
    def send_push_notification(user, title, message, data=None):
        """
        Send push notification to user if they have enabled push notifications
        Note: This is a placeholder implementation. In production, you would integrate
        with services like Firebase Cloud Messaging, OneSignal, or Web Push API
        """
        try:
            # Get user profile to check push notification preference
            profile = getattr(user, 'userprofile', None)
            if not profile or not profile.desktop_notifications:
                logger.info(f"Push notifications disabled for user {user.username}")
                return False
            
            # Placeholder for push notification implementation
            # In production, you would:
            # 1. Get user's device tokens from database
            # 2. Send notification via FCM, OneSignal, or Web Push API
            # 3. Handle delivery reports and errors
            
            logger.info(f"Push notification sent to user {user.username}: {title} - {message}")
            
            # For now, just log the notification
            # TODO: Implement actual push notification service
            return True
            
        except Exception as e:
            logger.error(f"Failed to send push notification to {user.username}: {str(e)}")
            return False
    
    @staticmethod
    def send_marketing_email(user, subject, message, template=None, context=None):
        """
        Send marketing email to user if they have enabled marketing emails
        """
        try:
            # Get user profile to check marketing email preference
            profile = getattr(user, 'userprofile', None)
            if not profile or not profile.allow_dm_from_non_contacts:
                logger.info(f"Marketing emails disabled for user {user.username}")
                return False
            
            # Prepare email content
            if template and context:
                html_message = render_to_string(template, context)
                plain_message = strip_tags(html_message)
            else:
                plain_message = message
                html_message = None
            
            # Add marketing footer
            marketing_footer = "\n\n---\nYou're receiving this email because you subscribed to marketing communications."
            plain_message += marketing_footer
            
            # Send email
            send_mail(
                subject=f"[Marketing] {subject}",
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False
            )
            
            logger.info(f"Marketing email sent to {user.email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send marketing email to {user.email}: {str(e)}")
            return False
    
    @staticmethod
    def notify_ticket_created(ticket):
        """Notify when a new ticket is created"""
        # Notify the user who created the ticket
        NotificationService.send_email_notification(
            user=ticket.created_by,
            subject=f"Ticket #{ticket.id} Created Successfully",
            message=f"Your ticket '{ticket.title}' has been created and is being reviewed.",
            template='emails/ticket_created.html',
            context={'ticket': ticket}
        )
        
        # Send push notification
        NotificationService.send_push_notification(
            user=ticket.created_by,
            title="Ticket Created",
            message=f"Your ticket '{ticket.title}' has been created successfully."
        )
    
    @staticmethod
    def notify_ticket_updated(ticket, updated_by=None):
        """Notify when a ticket is updated"""
        # Notify the ticket owner
        NotificationService.send_email_notification(
            user=ticket.created_by,
            subject=f"Ticket #{ticket.id} Updated",
            message=f"Your ticket '{ticket.title}' has been updated.",
            template='emails/ticket_updated.html',
            context={'ticket': ticket, 'updated_by': updated_by}
        )
        
        # Send push notification
        NotificationService.send_push_notification(
            user=ticket.created_by,
            title="Ticket Updated",
            message=f"Your ticket '{ticket.title}' has been updated."
        )
    
    @staticmethod
    def notify_ticket_resolved(ticket):
        """Notify when a ticket is resolved"""
        NotificationService.send_email_notification(
            user=ticket.created_by,
            subject=f"Ticket #{ticket.id} Resolved",
            message=f"Your ticket '{ticket.title}' has been marked as resolved.",
            template='emails/ticket_resolved.html',
            context={'ticket': ticket}
        )
        
        NotificationService.send_push_notification(
            user=ticket.created_by,
            title="Ticket Resolved",
            message=f"Your ticket '{ticket.title}' has been resolved."
        )
    
    @staticmethod
    def send_welcome_email(user):
        """Send welcome email to new users"""
        NotificationService.send_email_notification(
            user=user,
            subject="Welcome to TicketHub!",
            message="Welcome to TicketHub! We're excited to have you on board.",
            template='emails/welcome.html',
            context={'user': user}
        )
    
    @staticmethod
    def send_password_change_notification(user):
        """Send notification when password is changed"""
        NotificationService.send_email_notification(
            user=user,
            subject="Password Changed Successfully",
            message="Your password has been changed successfully. If you didn't make this change, please contact support immediately.",
            template='emails/password_changed.html',
            context={'user': user}
        )
        
        NotificationService.send_push_notification(
            user=user,
            title="Password Changed",
            message="Your password has been changed successfully."
        )
    
    @staticmethod
    def send_2fa_enabled_notification(user):
        """Send notification when 2FA is enabled"""
        NotificationService.send_email_notification(
            user=user,
            subject="Two-Factor Authentication Enabled",
            message="Two-factor authentication has been enabled on your account for enhanced security.",
            template='emails/2fa_enabled.html',
            context={'user': user}
        )
        
        NotificationService.send_push_notification(
            user=user,
            title="2FA Enabled",
            message="Two-factor authentication has been enabled on your account."
        )
    
    @staticmethod
    def send_marketing_campaign(user, campaign_name, subject, message):
        """Send marketing campaign email"""
        NotificationService.send_marketing_email(
            user=user,
            subject=subject,
            message=message,
            template='emails/marketing_campaign.html',
            context={
                'user': user,
                'campaign_name': campaign_name
            }
        )
