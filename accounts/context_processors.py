"""
Context processors to make common data available to all templates
"""
from django.db.models import Q
from notifications.models import Notification
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
        # Get unread notifications count
        context['unread_notifications'] = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        
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
