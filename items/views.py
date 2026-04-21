from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.conf import settings
import json
import requests as http_requests
from .models import Item, ItemImage, Claim, Category
from .forms import ItemForm, ItemImageForm, ItemSearchForm, ClaimForm
from .utils import validate_image_count, notify_matching_users
from notifications.models import Notification
from accounts.models import Transaction
from rewards.views import earn_points   # helper to award points
from django.utils import timezone
from datetime import timedelta


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
    # Check daily post limit
    recent_posts_count = Item.objects.filter(
        user=request.user,
        created_at__gte=timezone.now() - timedelta(days=1)
    ).count()
    
    limit = 20 if request.user.is_premium else 3
    if recent_posts_count >= limit:
        if request.user.is_premium:
            messages.error(request, 'You have reached your premium limit of 20 posts per 24 hours. Please try again later.')
        else:
            messages.error(request, 'You have reached your limit of 3 posts per 24 hours. Please come back later or upgrade to Premium to post more!')
        return redirect('items:item_list')

    if request.method == 'POST':
        form = ItemForm(request.POST, user=request.user)
        featured_image = request.FILES.get('featured_image')
        images = request.FILES.getlist('images')
        
        if form.is_valid():
            # Validate that at least featured image is uploaded
            if not featured_image:
                messages.error(request, 'Please upload a featured image for your item.')
                return render(request, 'items/post_item.html', {'form': form})
            
            # Count total images
            total_images = 1 + len(images)
            
            # Validate image count
            try:
                validate_image_count(request.user, total_images)
            except Exception as e:
                messages.error(request, str(e))
                return render(request, 'items/post_item.html', {'form': form})
            
            # Create item
            item = form.save(commit=False)
            item.user = request.user
            item.save()
            
            # Save featured image first (as primary)
            ItemImage.objects.create(
                item=item,
                image=featured_image,
                is_primary=True
            )
            
            # Save additional images
            for image in images:
                ItemImage.objects.create(
                    item=item,
                    image=image,
                    is_primary=False
                )
            
            # Notify users with matching items
            match_count = notify_matching_users(item)

            # Award points for posting a found item (encourages helpful participation)
            if item.item_type == 'found':
                earn_points(
                    user=request.user,
                    points=10,
                    reason=f'Posted a found item: "{item.title}"'
                )

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
    """Submit a claim for a lost or found item.
    - Lost item: another user claiming they have found it
    - Found item: the real owner claiming it belongs to them
    """
    # Works for any active item (both lost and found)
    item = get_object_or_404(Item, pk=pk, status='active')
    
    # Don't allow claiming a resolved item
    if item.status != 'active':
        messages.error(request, 'This item is no longer active and cannot be claimed.')
        return redirect('items:item_detail', pk=item.pk)
    
    # User cannot claim their own item
    if item.user == request.user:
        messages.error(request, 'You cannot claim your own item.')
        return redirect('items:item_detail', pk=item.pk)
    
    # Prevent duplicate claim by same user on same item
    existing_claim = Claim.objects.filter(item=item, claimant=request.user).first()
    if existing_claim:
        messages.warning(request, 'You have already submitted a claim for this item.')
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
                message=f'{request.user.username} has submitted an ownership claim for your found item "{item.title}".',
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
    """Mark item as resolved and handle reward payment via Khalti"""
    item = get_object_or_404(Item, pk=pk, user=request.user)
    
    # Get the approved claim for this item
    approved_claim = Claim.objects.filter(item=item, status='approved').first()
    
    if request.method == 'POST':
        # Mark item as resolved
        item.status = 'resolved'
        item.is_resolved = True
        item.save()
        
        # Add reward points to finder if claim exists
        if approved_claim:
            finder = approved_claim.claimant
            if item.reward_points > 0:
                finder.points_balance += item.reward_points
                finder.save(update_fields=['points_balance'])
                
                # Record transaction
                Transaction.objects.create(
                    user=finder,
                    transaction_type='earned',
                    points=item.reward_points,
                    description=f'Reward for finding "{item.title}"'
                )
        
        messages.success(request, 'Item marked as resolved!')
        return redirect('items:item_detail', pk=item.pk)
    
    context = {
        'item': item,
        'approved_claim': approved_claim,
        'khalti_public_key': settings.KHALTI_PUBLIC_KEY,
    }
    return render(request, 'items/mark_resolved.html', context)


@login_required
def verify_reward_payment(request, pk):
    """Verify Khalti payment for item reward"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'POST required'}, status=405)
    
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON'}, status=400)
    
    token = body.get('token', '')
    amount = body.get('amount', 0)
    item_id = body.get('item_id', '')
    
    if not all([token, amount, item_id]):
        return JsonResponse({'success': False, 'message': 'Missing required fields'}, status=400)
    
    try:
        item = Item.objects.get(pk=item_id, user=request.user)
    except Item.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Item not found'}, status=404)
    
    # DEBUG mode: auto-approve
    if settings.DEBUG:
        print(f'\n[REWARD KHALTI VERIFY] DEBUG mode — token={token} amount={amount}\n')
        item.reward_paid = True
        item.save(update_fields=['reward_paid'])
        return JsonResponse({
            'success': True,
            'message': 'Reward payment verified successfully!'
        })
    
    # PRODUCTION: verify with Khalti API
    khalti_api_url = settings.KHALTI_API_URL
    khalti_verify_url = f'{khalti_api_url}payment/verify/'
    headers = {'Authorization': f'Key {settings.KHALTI_SECRET_KEY}'}
    
    try:
        resp = http_requests.post(
            khalti_verify_url,
            data={'token': token, 'amount': amount},
            headers=headers,
            timeout=15
        )
    except Exception as exc:
        return JsonResponse({'success': False, 'message': f'Network error: {exc}'}, status=500)
    
    if resp.status_code == 200:
        item.reward_paid = True
        item.save(update_fields=['reward_paid'])
        return JsonResponse({'success': True, 'message': 'Reward payment verified!'})
    
    try:
        detail = resp.json()
    except:
        detail = resp.text[:200]
    
    return JsonResponse(
        {'success': False, 'message': 'Payment verification failed', 'detail': detail},
        status=400
    )


@login_required
def my_claims(request):
    """View claims submitted by the logged-in user"""
    claims = Claim.objects.filter(claimant=request.user).order_by('-created_at')
    
    # Pagination
    paginator = Paginator(claims, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'claims': page_obj,
    }
    return render(request, 'items/my_claims.html', context)


@login_required
def review_claim(request, claim_id):
    """Review and approve/reject a claim (for item owners)"""
    claim = get_object_or_404(Claim, pk=claim_id)
    
    # Only the item owner can review claims
    if claim.item.user != request.user:
        messages.error(request, "You do not have permission to review this claim.")
        return redirect('home')
        
    if request.method == 'POST':
        action = request.POST.get('action')
        admin_notes = request.POST.get('admin_notes', '')
        
        if action == 'approve':
            # Approve claim
            claim.status = 'approved'
            claim.admin_notes = admin_notes
            claim.save()
            
            # Resolve the item
            claim.item.status = 'resolved'
            claim.item.is_resolved = True
            claim.item.save()
            
            # Reject all other pending claims automatically
            other_claims = Claim.objects.filter(item=claim.item, status='pending').exclude(pk=claim.pk)
            for other_claim in other_claims:
                other_claim.status = 'rejected'
                other_claim.admin_notes = "Another claim was approved for this item."
                other_claim.save()
                
            # Notify claimant
            Notification.objects.create(
                user=claim.claimant,
                notification_type='claim',
                title='Claim Approved!',
                message=f'Your claim for "{claim.item.title}" has been approved!',
                link=f'/items/{claim.item.pk}/'
            )
            
            messages.success(request, 'Claim approved successfully. The item is now marked as resolved.')
            
        elif action == 'reject':
            # Reject claim
            claim.status = 'rejected'
            claim.admin_notes = admin_notes
            claim.save()
            
            # Notify claimant
            Notification.objects.create(
                user=claim.claimant,
                notification_type='claim',
                title='Claim Rejected',
                message=f'Your claim for "{claim.item.title}" was rejected.',
                link=f'/items/{claim.item.pk}/'
            )
            
            messages.success(request, 'Claim has been rejected.')
            
        return redirect('items:item_detail', pk=claim.item.pk)
        
    context = {
        'claim': claim,
        'item': claim.item,
    }
    return render(request, 'items/review_claim.html', context)
