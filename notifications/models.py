from django.db import models
from accounts.models import User


class Notification(models.Model):
    """In-app notifications for users"""
    NOTIFICATION_TYPE = (
        ('match', 'Matching Item Found'),
        ('message', 'New Message'),
        ('claim', 'Claim Submitted'),
        ('claim_approved', 'Claim Approved'),
        ('claim_rejected', 'Claim Rejected'),
        ('points_earned', 'Points Earned'),
        ('system', 'System Notification'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPE)
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=500, blank=True, help_text="URL to redirect when clicked")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.notification_type} for {self.user.username}"
    
    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']


class SystemNotification(models.Model):
    """Global system notifications from admin"""
    title = models.CharField(max_length=200)
    message = models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_system_notifications')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'system_notifications'
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class SystemNotificationReadStatus(models.Model):
    """Tracks which user has read which system notification"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='system_notification_read_statuses')
    notification = models.ForeignKey(SystemNotification, on_delete=models.CASCADE, related_name='read_statuses')
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'system_notification_read_statuses'
        unique_together = ('user', 'notification')

    def __str__(self):
        return f"{self.user.username} read {self.notification.title}"
