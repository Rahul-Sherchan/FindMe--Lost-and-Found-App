from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from .models import Item, ItemImage, Claim, Category
from .forms import ItemForm, ItemImageForm, ItemSearchForm, ClaimForm
from .utils import validate_image_count, notify_matching_users
from notifications.models import Notification


def item_list(request):
    """List all items with search and filter"""
    form = ItemSearchForm(request.GET or None)
    items = Item.objects.filter(is_approved=True, status='active')
    
    if form.is_valid():
        query = form.cleaned_data.get('query')
        item_type = form.cleaned_data.get('item_type')
        category = form.cleaned_data.get('category')
        location = form.cleaned_data.get('location')
        date_from = form.cleaned_data.get('date_from')
        date_to = form.cleaned_data.get('date_to')
        
        if query:
            items = items.filter(
                Q(title__icontains=query) | 
                Q(description__icontains=query)
            )
        
        if item_type:
            items = items.filter(item_type=item_type)
        
        if category:
            items = items.filter(category=category)
        
        if location:
            items = items.filter(location__icontains=location)
        
        if date_from:
            items = items.filter(date_lost_found__gte=date_from)
        
        if date_to:
            items = items.filter(date_lost_found__lte=date_to)
    
    # Pagination
    paginator = Paginator(items, 12)  # 12 items per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'form': form,
        'page_obj': page_obj,
        'items': page_obj,
    }
    return render(request, 'items/item_list.html', context)


@login_required
def post_item(request):
    """Post a new lost or found item"""
    if request.method == 'POST':
        form = ItemForm(request.POST, user=request.user)
        images = request.FILES.getlist('images')
        
        if form.is_valid():
            # Validate image count
            try:
                validate_image_count(request.user, len(images))
            except Exception as e:
                messages.error(request, str(e))
                return render(request, 'items/post_item.html', {'form': form})
            
            # Create item
            item = form.save(commit=False)
            item.user = request.user
            item.save()
            
            # Save images
            for idx, image in enumerate(images):
                ItemImage.objects.create(
                    item=item,
                    image=image,
                    is_primary=(idx == 0)  # First image is primary
                )
            
            # Notify users with matching items
            match_count = notify_matching_users(item)
            
            messages.success(request, f'Item posted successfully! {match_count} potential matches found.')
            return redirect('items:item_detail', pk=item.pk)
    else:
        # Pre-select item type from query parameter (?type=lost or ?type=found)
        initial = {}
        item_type = request.GET.get('type')
        if item_type in ('lost', 'found'):
            initial['item_type'] = item_type
        form = ItemForm(user=request.user, initial=initial)
    
    return render(request, 'items/post_item.html', {'form': form})


def item_detail(request, pk):
    """View item details"""
    item = get_object_or_404(Item, pk=pk)
    
    # Increment view count
    item.views_count += 1
    item.save(update_fields=['views_count'])
    
    # Get all images
    images = item.images.all()
    
    # Get claims if user is the owner
    claims = None
    if request.user.is_authenticated and request.user == item.user:
        claims = item.claims.all()
    
    context = {
        'item': item,
        'images': images,
        'claims': claims,
    }
    return render(request, 'items/item_detail.html', context)


@login_required
def my_items(request):
    """View user's posted items"""
    items = Item.objects.filter(user=request.user).order_by('-created_at')
    
    # Pagination
    paginator = Paginator(items, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'items': page_obj,
    }
    return render(request, 'items/my_items.html', context)


@login_required
def edit_item(request, pk):
    """Edit an item"""
    item = get_object_or_404(Item, pk=pk, user=request.user)
    
    if request.method == 'POST':
        form = ItemForm(request.POST, instance=item, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Item updated successfully!')
            return redirect('items:item_detail', pk=item.pk)
    else:
        form = ItemForm(instance=item, user=request.user)
    
    context = {
        'form': form,
        'item': item,
    }
    return render(request, 'items/edit_item.html', context)


@login_required
def delete_item(request, pk):
    """Delete an item"""
    item = get_object_or_404(Item, pk=pk, user=request.user)
    
    if request.method == 'POST':
        item.delete()
        messages.success(request, 'Item deleted successfully!')
        return redirect('items:my_items')
    
    return render(request, 'items/delete_confirm.html', {'item': item})


@login_required
def submit_claim(request, pk):
    """Submit a claim for a lost item"""
    item = get_object_or_404(Item, pk=pk, item_type='lost', status='active')
    
    # Check if user already submitted a claim
    existing_claim = Claim.objects.filter(item=item, claimant=request.user).first()
    if existing_claim:
        messages.warning(request, 'You have already submitted a claim for this item.')
        return redirect('items:item_detail', pk=item.pk)
    
    # User cannot claim their own item
    if item.user == request.user:
        messages.error(request, 'You cannot claim your own item.')
        return redirect('items:item_detail', pk=item.pk)
    
    if request.method == 'POST':
        form = ClaimForm(request.POST, request.FILES)
        if form.is_valid():
            claim = form.save(commit=False)
            claim.item = item
            claim.claimant = request.user
            claim.save()
            
            # Notify item owner
            Notification.objects.create(
                user=item.user,
                notification_type='claim',
                title='New Claim Submitted',
                message=f'{request.user.username} has submitted a claim for your lost item "{item.title}".',
                link=f'/items/{item.pk}/'
            )
            
            messages.success(request, 'Claim submitted successfully! Waiting for admin approval.')
            return redirect('items:item_detail', pk=item.pk)
    else:
        form = ClaimForm()
    
    context = {
        'form': form,
        'item': item,
    }
    return render(request, 'items/submit_claim.html', context)


@login_required
def mark_as_resolved(request, pk):
    """Mark item as resolved"""
    item = get_object_or_404(Item, pk=pk, user=request.user)
    
    if request.method == 'POST':
        item.status = 'resolved'
        item.save()
        messages.success(request, 'Item marked as resolved!')
        return redirect('items:item_detail', pk=item.pk)
    
    return render(request, 'items/mark_resolved.html', {'item': item})
