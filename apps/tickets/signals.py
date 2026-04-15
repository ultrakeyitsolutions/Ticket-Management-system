# Signals for automatic notification creation when tickets are created or updated

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Ticket
from dashboards.models import Notification
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Ticket)
def create_ticket_notification(sender, instance, created, **kwargs):
    """Create notification when ticket is created or updated"""
    try:
        # Determine notification type and message based on ticket status
        if instance.status == 'Open':
            title = f"New Ticket Created: {instance.ticket_id}"
            message = f"A new ticket '{instance.title}' has been created and requires your attention."
            notification_type = 'ticket'
            priority = 'high'
            action_text = 'View Ticket'
            action_url = f"/dashboard/admin-dashboard/ticket/{instance.ticket_id}/"
        elif instance.status == 'In Progress':
            title = f"Ticket Status Update: {instance.ticket_id}"
            message = f"Ticket '{instance.title}' status has been updated to 'In Progress'."
            notification_type = 'ticket'
            priority = 'medium'
            action_text = 'View Ticket'
            action_url = f"/dashboard/admin-dashboard/ticket/{instance.ticket_id}/"
        elif instance.status == 'Resolved':
            title = f"Ticket Resolved: {instance.ticket_id}"
            message = f"Ticket '{instance.title}' has been marked as resolved."
            notification_type = 'ticket'
            priority = 'low'
            action_text = 'View Ticket'
            action_url = f"/dashboard/admin-dashboard/ticket/{instance.ticket_id}/"
        elif instance.status == 'Closed':
            title = f"Ticket Closed: {instance.ticket_id}"
            message = f"Ticket '{instance.title}' has been closed."
            notification_type = 'ticket'
            priority = 'low'
            action_text = 'View Ticket'
            action_url = f"/dashboard/admin-dashboard/ticket/{instance.ticket_id}/"
        else:
            return  # Don't create notification for other statuses
        
        # Create notifications for different recipients
        notifications_to_create = []
        
        # Always notify admin users for new tickets
        if created:
            admin_users = User.objects.filter(is_superuser=True)
            for admin_user in admin_users:
                notifications_to_create.append({
                    'recipient': admin_user,
                    'title': title,
                    'message': message,
                    'notification_type': notification_type,
                    'priority': priority,
                    'action_url': action_url,
                    'action_text': action_text,
                    'ticket': instance
                })
        
        # Notify ticket creator when their ticket status changes
        if not created and instance.created_by:
            notifications_to_create.append({
                'recipient': instance.created_by,
                'title': f"Your Ticket Status Update: {instance.ticket_id}",
                'message': f"Your ticket '{instance.title}' status has been updated to '{instance.status}'.",
                'notification_type': 'system',
                'priority': 'medium',
                'action_url': f"/dashboard/user-dashboard/ticket/{instance.ticket_id}/",
                'action_text': 'View Ticket',
                'ticket': instance
            })
        
        # Notify assigned user when ticket is assigned or status changes
        if hasattr(instance, 'assigned_to') and instance.assigned_to:
            notifications_to_create.append({
                'recipient': instance.assigned_to,
                'title': f"Ticket Assignment: {instance.ticket_id}",
                'message': f"Ticket '{instance.title}' has been assigned to you.",
                'notification_type': 'user',
                'priority': 'medium',
                'action_url': f"/dashboard/user-dashboard/ticket/{instance.ticket_id}/",
                'action_text': 'View Ticket',
                'ticket': instance
            })
        
        # Create all notifications
        for notification_data in notifications_to_create:
            Notification.objects.create(**notification_data)
        
        logger.info(f"Created {len(notifications_to_create)} notifications for ticket {instance.ticket_id}")
        
    except Exception as e:
        logger.error(f"Error creating ticket notification: {e}")


@receiver(post_save, sender=Ticket)
def create_ticket_assignment_notification(sender, instance, created, **kwargs):
    """Create notification when ticket is assigned to someone"""
    try:
        # Only create notifications for assignments, not new tickets
        if created:
            return  # Skip for new tickets, handled above
            
        # Check if assigned_to field has changed
        if hasattr(instance, 'assigned_to') and instance.assigned_to:
            # Get the previous assigned user (this is a simplified check)
            # In a real implementation, you'd track the previous value
            
            title = f"Ticket Assigned: {instance.ticket_id}"
            message = f"Ticket '{instance.title}' has been assigned to {instance.assigned_to.get_full_name() or instance.assigned_to.username}."
            notification_type = 'ticket'
            priority = 'medium'
            action_text = 'View Ticket'
            action_url = f"/dashboard/admin-dashboard/ticket/{instance.ticket_id}/"
            
            # Get the user who should receive the notification
            recipient = instance.assigned_to
            
            # Create the notification
            Notification.objects.create(
                recipient=recipient,
                title=title,
                message=message,
                notification_type=notification_type,
                priority=priority,
                action_url=action_url,
                action_text=action_text,
                ticket=instance  # Link to the ticket
            )
            
            logger.info(f"Created assignment notification for ticket {instance.ticket_id}")
        
    except Exception as e:
        logger.error(f"Error creating assignment notification: {e}")


@receiver(post_delete, sender=Ticket)
def create_ticket_deletion_notification(sender, instance, **kwargs):
    """Create notification when ticket is deleted"""
    try:
        title = f"Ticket Deleted: {instance.ticket_id}"
        message = f"Ticket '{instance.title}' has been deleted."
        notification_type = 'ticket'
        priority = 'medium'
        action_text = None  # No action since ticket is deleted
        action_url = None
        
        # Get the admin user who should receive the notification
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            return
            
        # Create the notification
        Notification.objects.create(
            recipient=admin_user,
            title=title,
            message=message,
            notification_type=notification_type,
            priority=priority,
            action_url=action_url,
            action_text=action_text,
            ticket=None  # Ticket is deleted, so no link
        )
        
        logger.info(f"Created deletion notification for ticket {instance.ticket_id}")
        
    except Exception as e:
        logger.error(f"Error creating deletion notification: {e}")
