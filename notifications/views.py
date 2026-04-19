from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Notification


@login_required
def notification_list(request):
    """List all notifications for the current user"""
    notifications = Notification.objects.filter(user=request.user)
    unread_notifications = notifications.filter(is_read=False)
    
    context = {
        'notifications': notifications,
        'unread_count': unread_notifications.count(),
    }
    return render(request, 'notifications/notification_list.html', context)


@login_required
def mark_as_read(request, pk):
    """Mark a notification as read"""
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.is_read = True
    notification.save()
    
    # If it's an AJAX request, return JSON
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.headers.get('Accept') == 'application/json':
        return JsonResponse({'status': 'success'})
    
    # Redirect to the link if provided
    if notification.link:
        return redirect(notification.link)
    
    return redirect('notifications:notification_list')


@login_required
def mark_all_as_read(request):
    """Mark all notifications as read"""
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return redirect('notifications:notification_list')

from django.http import JsonResponse
from .models import SystemNotification, SystemNotificationReadStatus

@login_required
def mark_system_as_read(request, pk):
    """Mark a global system notification as read for the current user."""
    sys_notif = get_object_or_404(SystemNotification, pk=pk)
    
    # Create the read status mapping for this user specifically
    SystemNotificationReadStatus.objects.get_or_create(
        user=request.user,
        notification=sys_notif,
        defaults={'is_read': True}
    )
    
    # If it's an AJAX request, return JSON
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.headers.get('Accept') == 'application/json':
        return JsonResponse({'status': 'success'})
        
    return redirect(request.META.get('HTTP_REFERER', 'notifications:notification_list'))
