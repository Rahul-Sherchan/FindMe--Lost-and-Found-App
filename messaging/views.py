from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages as django_messages
from django.db.models import Q
from .models import Conversation, Message
from items.models import Item
from notifications.models import Notification


@login_required
def conversation_list(request):
    """List all conversations for the current user"""
    conversations = Conversation.objects.filter(
        Q(participant1=request.user) | Q(participant2=request.user)
    ).order_by('-updated_at')
    
    # Get unread message count for each conversation
    for conv in conversations:
        conv.unread_count = conv.messages.filter(
            is_read=False
        ).exclude(sender=request.user).count()
    
    context = {
        'conversations': conversations,
    }
    return render(request, 'messaging/conversation_list.html', context)


@login_required
def conversation_detail(request, pk):
    """View and send messages in a conversation"""
    conversation = get_object_or_404(
        Conversation,
        pk=pk
    )
    
    # Check if user is a participant
    if request.user not in [conversation.participant1, conversation.participant2]:
        django_messages.error(request, 'You do not have access to this conversation.')
        return redirect('messaging:conversation_list')
    
    # Mark messages as read
    conversation.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)
    
    # Handle new message
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        if content:
            message = Message.objects.create(
                conversation=conversation,
                sender=request.user,
                content=content
            )
            
            # Update conversation timestamp
            conversation.save()
            
            # Notify the other participant
            other_user = conversation.get_other_participant(request.user)
            if conversation.item:
                msg_text = f'{request.user.username} sent you a message about "{conversation.item.title}"'
            else:
                msg_text = f'{request.user.username} sent you a message (Admin Support)'
                
            Notification.objects.create(
                user=other_user,
                notification_type='message',
                title='New Message',
                message=msg_text,
                link=f'/messaging/{conversation.pk}/'
            )
            
            return redirect('messaging:conversation_detail', pk=conversation.pk)
    
    messages = conversation.messages.all()
    other_user = conversation.get_other_participant(request.user)
    
    context = {
        'conversation': conversation,
        'chat_messages': messages,
        'other_user': other_user,
    }
    return render(request, 'messaging/conversation_detail.html', context)


@login_required
def start_conversation(request, item_pk):
    """Start a new conversation about an item"""
    item = get_object_or_404(Item, pk=item_pk)
    
    # Cannot message yourself
    if item.user == request.user:
        django_messages.error(request, 'You cannot message yourself.')
        return redirect('items:item_detail', pk=item.pk)
    
    # Check if conversation already exists
    existing_conv = Conversation.objects.filter(
        item=item,
        participant1__in=[request.user, item.user],
        participant2__in=[request.user, item.user]
    ).first()
    
    if existing_conv:
        return redirect('messaging:conversation_detail', pk=existing_conv.pk)
    
    # Create new conversation
    conversation = Conversation.objects.create(
        item=item,
        participant1=request.user,
        participant2=item.user
    )
    
    django_messages.success(request, 'Conversation started! Send a message to the item owner.')
    return redirect('messaging:conversation_detail', pk=conversation.pk)
@login_required
def start_admin_conversation(request, user_pk):
    """Start a new conversation with a user (Admin only)"""
    if not (request.user.is_staff or getattr(request.user, 'user_type', None) == 'admin'):
        django_messages.error(request, 'Not authorized to start admin conversations.')
        return redirect('home')
        
    other_user = get_object_or_404(User, pk=user_pk)
    
    # Cannot message yourself
    if other_user == request.user:
        django_messages.error(request, 'You cannot message yourself.')
        return redirect('admin_dashboard:manage_users')
    
    # Check if conversation already exists
    existing_conv = Conversation.objects.filter(
        item__isnull=True,
        participant1__in=[request.user, other_user],
        participant2__in=[request.user, other_user]
    ).first()
    
    if existing_conv:
        return redirect('messaging:conversation_detail', pk=existing_conv.pk)
    
    # Create new conversation
    conversation = Conversation.objects.create(
        item=None,
        participant1=request.user,
        participant2=other_user
    )
    
    django_messages.success(request, f'Admin conversation started with {other_user.username}.')
    return redirect('messaging:conversation_detail', pk=conversation.pk)
