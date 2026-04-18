"""
Context processors to make common data available to all templates
"""
from django.db.models import Q
from notifications.models import Notification, SystemNotification, SystemNotificationReadStatus
from messaging.models import Message, Conversation


def notification_counts(request):
    """
    Add unread notification and message counts to context
    Available to all templates
    """
    context = {
        'unread_notifications': 0,
        'unread_messages': 0,
    }
    
    if request.user.is_authenticated:
        # Get top 5 personal notifications
        personal_notifs = Notification.objects.filter(
            user=request.user
        ).order_by('-created_at')[:5]
        
        unread_personal_count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        
        # Get top 5 system notifications
        system_notifs = SystemNotification.objects.all().order_by('-created_at')[:5]
        read_system_ids = SystemNotificationReadStatus.objects.filter(
            user=request.user,
            is_read=True
        ).values_list('notification_id', flat=True)
        
        # Process system notifications with mapped read statuses
        system_notifs_with_status = []
        unread_sys_count_local = 0
        for notif in system_notifs:
            is_read = notif.id in read_system_ids
            if not is_read:
                unread_sys_count_local += 1
            system_notifs_with_status.append({
                'id': notif.id,
                'title': notif.title,
                'message': notif.message,
                'created_at': notif.created_at,
                'is_read': is_read,
                'created_by': notif.created_by
            })
            
        # Optional: total unread system notifications
        total_unread_sys_count = SystemNotification.objects.exclude(id__in=read_system_ids).count()
        
        context['unread_notifications'] = unread_personal_count + total_unread_sys_count
        context['personal_notifications'] = personal_notifs
        context['system_notifications'] = system_notifs_with_status
        context['unread_personal_count'] = unread_personal_count
        context['unread_system_count'] = total_unread_sys_count
        
        # Get unread messages count
        conversations = Conversation.objects.filter(
            Q(participant1=request.user) | Q(participant2=request.user)
        )
        unread_messages = Message.objects.filter(
            conversation__in=conversations,
            is_read=False
        ).exclude(sender=request.user).count()
        
        context['unread_messages'] = unread_messages
    
    return context
