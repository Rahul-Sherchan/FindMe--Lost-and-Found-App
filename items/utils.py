from django.core.exceptions import ValidationError
from notifications.models import Notification


def validate_image_count(user, image_count):
    """
    Validate if user can upload the specified number of images
    Returns True if allowed, raises ValidationError otherwise
    """
    limit = user.image_upload_limit
    
    if limit is None:  # Premium user - unlimited
        return True
    
    if image_count > limit:
        raise ValidationError(
            f'Normal users can upload maximum {limit} images per post. '
            f'Upgrade to premium for unlimited uploads.'
        )
    
    return True


def find_matching_items(new_item):
    """
    Find items that match the new item based on category and location
    Returns queryset of matching items
    """
    from .models import Item
    
    # Determine opposite item type
    opposite_type = 'found' if new_item.item_type == 'lost' else 'lost'
    
    # Find items with same category and similar location
    matching_items = Item.objects.filter(
        item_type=opposite_type,
        category=new_item.category,
        status='active'
    ).exclude(user=new_item.user)
    
    # Filter by location (case-insensitive contains)
    if new_item.location:
        matching_items = matching_items.filter(
            location__icontains=new_item.location
        )
    
    return matching_items


def notify_matching_users(new_item):
    """
    Create notifications for users with matching items
    """
    matching_items = find_matching_items(new_item)
    
    for item in matching_items:
        # Create notification for the owner of matching item
        Notification.objects.create(
            user=item.user,
            notification_type='match',
            title='Matching Item Found!',
            message=f'A {new_item.get_item_type_display()} matching your {item.get_item_type_display()} "{item.title}" has been posted.',
            link=f'/items/{new_item.id}/'
        )
    
    return matching_items.count()
