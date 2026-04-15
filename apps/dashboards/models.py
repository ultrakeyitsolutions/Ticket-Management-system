from django.db import models
from django.contrib.auth.models import User
from tickets.models import Ticket
import uuid

# Create your models here.

class SiteSettings(models.Model):
    company_name = models.CharField(max_length=200, blank=True, default="")
    website_url = models.URLField(blank=True, default="")
    contact_email = models.EmailField(blank=True, default="")
    contact_phone = models.CharField(max_length=50, blank=True, default="")
    address = models.TextField(blank=True, default="")

    default_language = models.CharField(max_length=50, blank=True, default="English (United States)")
    time_zone = models.CharField(max_length=50, blank=True, default="UTC")
    date_format = models.CharField(max_length=20, blank=True, default="YYYY-MM-DD")
    time_format = models.CharField(max_length=20, blank=True, default="24-hour")
    first_day_of_week = models.IntegerField(blank=True, default=1)
    currency = models.CharField(max_length=50, blank=True, default="USD - US Dollar ($)")

    maintenance_mode = models.BooleanField(default=False)
    user_registration = models.BooleanField(default=True)
    email_verification = models.BooleanField(default=True)
    remember_me = models.BooleanField(default=True)
    show_tutorial = models.BooleanField(default=True)

    theme = models.CharField(max_length=10, blank=True, default="light")
    primary_color = models.CharField(max_length=7, blank=True, default="#0d6efd")
    fixed_header = models.BooleanField(default=True)
    fixed_sidebar = models.BooleanField(default=True)
    collapsed_sidebar = models.BooleanField(default=False)
    # Company branding
    company_logo = models.ImageField(upload_to='site/', blank=True, null=True)
    collapsed_logo = models.BooleanField(default=False)

    # Ticket settings
    default_ticket_status = models.CharField(max_length=50, blank=True, default="Open")
    default_ticket_priority = models.CharField(max_length=20, blank=True, default="Medium")
    auto_ticket_assignment = models.BooleanField(default=True)
    allow_ticket_reopen = models.BooleanField(default=True)
    first_response_hours = models.IntegerField(blank=True, default=24)
    resolution_time_hours = models.IntegerField(blank=True, default=72)
    sla_business_hours = models.CharField(max_length=100, blank=True, default="Business Hours (9 AM - 5 PM, Mon-Fri)")

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'dashboards'

    def __str__(self):
        return f"Site Settings ({self.pk})"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class Faq(models.Model):
    """Simple FAQ entry model for user-visible help articles."""
    QUESTION_MAX = 512
    question = models.CharField(max_length=QUESTION_MAX)
    answer = models.TextField()
    category = models.CharField(max_length=120, blank=True, default='')
    order = models.IntegerField(default=0)
    is_published = models.BooleanField(default=True)

    class Meta:
        app_label = 'dashboards'
        ordering = ['order', 'id']

    def __str__(self):
        return self.question


class Notification(models.Model):
    """Notification model for admin dashboard"""
    
    NOTIFICATION_TYPES = [
        ('ticket', 'Ticket'),
        ('system', 'System'),
        ('alert', 'Alert'),
        ('user', 'User'),
        ('performance', 'Performance'),
    ]
    
    PRIORITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='admin_notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='system')
    priority = models.CharField(max_length=10, choices=PRIORITY_LEVELS, default='medium')
    
    # Optional related objects
    ticket = models.ForeignKey(Ticket, on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications')
    
    # Status and timestamps
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Action URLs
    action_url = models.URLField(max_length=500, blank=True, null=True)
    action_text = models.CharField(max_length=50, blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read', '-created_at']),
            models.Index(fields=['notification_type']),
            models.Index(fields=['priority']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.recipient.username}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = models.timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
    
    @property
    def icon_class(self):
        """Return Bootstrap icon class based on notification type"""
        icon_map = {
            'ticket': 'bi-ticket-detailed',
            'system': 'bi-gear',
            'alert': 'bi-exclamation-triangle',
            'user': 'bi-person',
            'performance': 'bi-graph-up',
        }
        return icon_map.get(self.notification_type, 'bi-bell')
    
    @property
    def css_class(self):
        """Return CSS class for notification styling"""
        class_map = {
            'ticket': 'ticket',
            'system': 'system',
            'alert': 'warning',
            'user': 'system',
            'performance': 'warning',
        }
        return class_map.get(self.notification_type, 'system')
    
    @property
    def time_ago(self):
        """Return human readable time ago"""
        from django.utils import timezone
        import datetime
        
        now = timezone.now()
        diff = now - self.created_at
        
        if diff < datetime.timedelta(minutes=1):
            return "Just now"
        elif diff < datetime.timedelta(hours=1):
            minutes = int(diff.total_seconds() / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif diff < datetime.timedelta(days=1):
            hours = int(diff.total_seconds() / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif diff < datetime.timedelta(days=7):
            days = diff.days
            return f"{days} day{'s' if days != 1 else ''} ago"
        else:
            return self.created_at.strftime("%b %d, %Y")
