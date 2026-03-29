from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
import json
from datetime import date, timedelta, datetime
from django.db.models import Count
from django.db.models.functions import TruncMonth, TruncWeek
from accounts.models import User, Transaction
from items.models import Item, Claim
from notifications.models import Notification

def is_admin(user):
    return user.is_authenticated and (user.is_staff or user.user_type == 'admin')

def get_pending_claims_count():
    return Claim.objects.filter(status='pending').count()

@login_required
@user_passes_test(is_admin)
def dashboard(request):
    total_users = User.objects.count()
    premium_users = User.objects.filter(is_premium=True).count()
    total_items = Item.objects.count()
    lost_items = Item.objects.filter(item_type='lost').count()
    found_items = Item.objects.filter(item_type='found').count()
    pending_claims_count = get_pending_claims_count()
    resolved_items = Item.objects.filter(status='resolved').count()
    
    recent_items = Item.objects.select_related('user', 'category').order_by('-created_at')[:5]
    recent_claims = Claim.objects.select_related('claimant', 'item', 'item__user').order_by('-created_at')[:5]
    recent_users = User.objects.all().order_by('-date_joined')[:6]
    
    context = {
        'total_users': total_users,
        'premium_users': premium_users,
        'total_items': total_items,
        'lost_items': lost_items,
        'found_items': found_items,
        'pending_claims': pending_claims_count,
        'resolved_items': resolved_items,
        'recent_items': recent_items,
        'recent_claims': recent_claims,
        'recent_users': recent_users,
        'pending_claims_count': pending_claims_count,
    }
    return render(request, 'admin_dashboard/dashboard.html', context)

@login_required
@user_passes_test(is_admin)
def manage_users(request):
    users = User.objects.prefetch_related('subscriptions').order_by('-date_joined')
    context = {
        'users': users,
        'pending_claims_count': get_pending_claims_count(),
    }
    return render(request, 'admin_dashboard/manage_users.html', context)

@login_required
@user_passes_test(is_admin)
def manage_posts(request):
    items = Item.objects.select_related('user', 'category').order_by('-created_at')
    
    ftype = request.GET.get('type')
    if ftype in ['lost', 'found']:
        items = items.filter(item_type=ftype)
        
    fstatus = request.GET.get('status')
    if fstatus in ['active', 'resolved', 'expired']:
        items = items.filter(status=fstatus)

    context = {
        'items': items,
        'pending_claims_count': get_pending_claims_count(),
    }
    return render(request, 'admin_dashboard/manage_posts.html', context)

@login_required
@user_passes_test(is_admin)
def manage_claims(request):
    claims = Claim.objects.select_related('claimant', 'item', 'item__user', 'reviewed_by').order_by('-created_at')
    
    fstatus = request.GET.get('status')
    if fstatus in ['pending', 'approved', 'rejected']:
        claims = claims.filter(status=fstatus)
        
    context = {
        'claims': claims,
        'pending_claims_count': get_pending_claims_count(),
    }
    return render(request, 'admin_dashboard/manage_claims.html', context)

@login_required
@user_passes_test(is_admin)
def approve_claim(request, pk):
    claim = get_object_or_404(Claim, pk=pk)
    
    if claim.status != 'pending':
        messages.warning(request, f'This claim is already {claim.get_status_display()}.')
        return redirect('admin_dashboard:manage_claims')
        
    if request.method == 'POST':
        with db_transaction.atomic():
            claim.status = 'approved'
            claim.reviewed_by = request.user
            claim.reviewed_at = timezone.now()
            claim.admin_notes = request.POST.get('admin_notes', '')
            claim.save()
            
            # Set claim.item.status = 'resolved' and save
            claim.item.status = 'resolved'
            claim.item.save()
            
            reward_points = claim.item.reward_points
            if reward_points > 0:
                claim.claimant.points_balance += reward_points
                claim.claimant.save(update_fields=['points_balance'])
                Transaction.objects.create(
                    user=claim.claimant, 
                    transaction_type='earned', 
                    points=reward_points, 
                    description=f'Reward for finding "{claim.item.title}"'
                )
            
            msg = 'Claim Approved!'
            if reward_points > 0:
                msg += f' You earned {reward_points} points!'
                
            Notification.objects.create(
                user=claim.claimant,
                notification_type='claim_approved',
                title='Claim Approved!',
                message=msg,
                link=f'/items/{claim.item.pk}/'
            )
            
            if claim.item.user != claim.claimant:
                Notification.objects.create(
                    user=claim.item.user,
                    notification_type='claim_approved',
                    title='Claim Approved',
                    message=f'The claim for your item "{claim.item.title}" has been approved by admin.',
                    link=f'/items/{claim.item.pk}/'
                )
                
            other_claims = Claim.objects.filter(item=claim.item, status='pending').exclude(pk=claim.pk)
            for other in other_claims:
                other.status = 'rejected'
                other.reviewed_by = request.user
                other.reviewed_at = timezone.now()
                other.admin_notes = 'Auto-rejected: another claim was approved.'
                other.save()
                
                Notification.objects.create(
                    user=other.claimant,
                    notification_type='claim_rejected',
                    title='Claim Auto-Rejected',
                    message=f'Your claim for "{claim.item.title}" was rejected because another claim was approved.',
                    link=f'/items/{claim.item.pk}/'
                )
                
        if reward_points > 0:
            messages.success(request, f'{reward_points} points awarded to {claim.claimant.username}.')
        else:
            messages.success(request, 'Claim approved. No reward points on this item.')
            
        return redirect('admin_dashboard:manage_claims')
        
    context = {
        'claim': claim,
        'pending_claims_count': get_pending_claims_count(),
    }
    return render(request, 'admin_dashboard/approve_claim.html', context)

@login_required
@user_passes_test(is_admin)
def reject_claim(request, pk):
    claim = get_object_or_404(Claim, pk=pk)
    
    if claim.status != 'pending':
        messages.warning(request, f'This claim is already {claim.get_status_display()}.')
        return redirect('admin_dashboard:manage_claims')
        
    if request.method == 'POST':
        claim.status = 'rejected'
        claim.reviewed_by = request.user
        claim.reviewed_at = timezone.now()
        admin_notes = request.POST.get('admin_notes', '')
        claim.admin_notes = admin_notes
        claim.save()
        
        base_msg = f'Your claim for "{claim.item.title}" has been rejected.'
        if admin_notes:
            base_msg += f' Reason: {admin_notes}'
            
        Notification.objects.create(
            user=claim.claimant,
            notification_type='claim_rejected',
            title='Claim Rejected',
            message=base_msg,
            link=f'/items/{claim.item.pk}/'
        )
        
        messages.success(request, 'Claim rejected.')
        return redirect('admin_dashboard:manage_claims')
        
    context = {
        'claim': claim,
        'pending_claims_count': get_pending_claims_count(),
    }
    return render(request, 'admin_dashboard/reject_claim.html', context)

@login_required
@user_passes_test(is_admin)
def approve_item(request, pk):
    item = get_object_or_404(Item, pk=pk)
    
    if request.method == 'POST':
        item.is_approved = True
        item.save(update_fields=['is_approved'])
        
        Notification.objects.create(
            user=item.user,
            notification_type='item_approved',
            title='Your Post is Live!',
            message=f'Your post "{item.title}" has been approved and is now visible.',
            link=f'/items/{item.pk}/'
        )
        
        messages.success(request, f'Post "{item.title}" has been approved.')
        return redirect('admin_dashboard:manage_posts')
    
    return redirect('admin_dashboard:manage_posts')

@login_required
@user_passes_test(is_admin)
def delete_post(request, pk):
    item = get_object_or_404(Item, pk=pk)
    
    if request.method == 'POST':
        item.delete()
        messages.success(request, 'Post deleted successfully.')
        return redirect('admin_dashboard:manage_posts')
        
    context = {
        'item': item,
        'pending_claims_count': get_pending_claims_count(),
    }
    return render(request, 'admin_dashboard/delete_post.html', context)

@login_required
@user_passes_test(is_admin)
def toggle_user_active(request, pk):
    user = get_object_or_404(User, pk=pk)
    
    if request.method == 'POST':
        user.is_active = not user.is_active
        user.save(update_fields=['is_active'])
        if user.is_active:
            messages.success(request, f'User {user.username} has been reactivated.')
        else:
            messages.success(request, f'User {user.username} has been suspended.')
    
    return redirect('admin_dashboard:manage_users')

@login_required
@user_passes_test(is_admin)
def suspend_user(request, pk):
    return toggle_user_active(request, pk)

@login_required
@user_passes_test(is_admin)
def user_detail(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    subscriptions = user_obj.subscriptions.all().order_by('-start_date')
    transactions = user_obj.transactions.all().order_by('-created_at')
    items = user_obj.items.all().order_by('-created_at')
    claims = user_obj.claims.all().order_by('-created_at')
    
    context = {
        'user_obj': user_obj,
        'subscriptions': subscriptions,
        'transactions': transactions,
        'items': items,
        'claims': claims,
        'pending_claims_count': get_pending_claims_count(),
    }
    return render(request, 'admin_dashboard/user_detail.html', context)


@login_required
@user_passes_test(is_admin)
def reports(request):
    # STEP 1: Read GET params
    view_mode = request.GET.get('view', 'monthly')  # 'monthly' or 'weekly'
    start_str = request.GET.get('start', '')
    end_str   = request.GET.get('end', '')

    # STEP 2: Parse or default dates
    today = date.today()
    try:
        if start_str and end_str:
            start = datetime.strptime(start_str, '%Y-%m-%d').date()
            end   = datetime.strptime(end_str,   '%Y-%m-%d').date()
        else:
            raise ValueError("use defaults")
    except (ValueError, TypeError):
        if view_mode == 'weekly':
            start = today - timedelta(weeks=7)
        else:
            start = today - timedelta(days=365)
        end = today

    # STEP 3: Summary counts (filter by created_at date range)
    base_qs = Item.objects.filter(
        created_at__date__gte=start,
        created_at__date__lte=end
    )
    total_lost     = base_qs.filter(item_type='lost').count()
    total_found    = base_qs.filter(item_type='found').count()
    total_resolved = base_qs.filter(status='resolved').count()
    total_items    = total_lost + total_found

    # STEP 4: Compute percentages (avoid division by zero)
    lost_pct    = round(total_lost    / total_items * 100) if total_items > 0 else 0
    found_pct   = round(total_found   / total_items * 100) if total_items > 0 else 0
    return_rate = round(total_resolved / total_items * 100) if total_items > 0 else 0

    # STEP 5: Chart data grouped by period
    trunc_fn = TruncMonth if view_mode == 'monthly' else TruncWeek

    def get_period_data(queryset):
        return {
            row['period']: row['count']
            for row in queryset.annotate(period=trunc_fn('created_at'))
                               .values('period')
                               .annotate(count=Count('id'))
                               .order_by('period')
        }

    lost_data     = get_period_data(
        Item.objects.filter(item_type='lost',
            created_at__date__gte=start, created_at__date__lte=end))
    found_data    = get_period_data(
        Item.objects.filter(item_type='found',
            created_at__date__gte=start, created_at__date__lte=end))
    resolved_data = get_period_data(
        Item.objects.filter(status='resolved',
            created_at__date__gte=start, created_at__date__lte=end))

    # Collect all unique periods from all three datasets
    all_periods = sorted(
        set(lost_data.keys()) | set(found_data.keys()) | set(resolved_data.keys())
    )

    # Format labels based on view mode
    if view_mode == 'monthly':
        chart_labels = [p.strftime('%b %Y') for p in all_periods]
    else:
        chart_labels = [f"W/E {p.strftime('%d %b')}" for p in all_periods]

    chart_lost     = [lost_data.get(p, 0)     for p in all_periods]
    chart_found    = [found_data.get(p, 0)    for p in all_periods]
    chart_resolved = [resolved_data.get(p, 0) for p in all_periods]

    # STEP 6: Recent resolved items table
    recent_resolved = Item.objects.filter(
        status='resolved',
        created_at__date__gte=start,
        created_at__date__lte=end
    ).select_related('user', 'category').order_by('-created_at')[:15]

    context = {
        'total_lost':      total_lost,
        'total_found':     total_found,
        'total_resolved':  total_resolved,
        'total_items':     total_items,
        'lost_pct':        lost_pct,
        'found_pct':       found_pct,
        'return_rate':     return_rate,
        'chart_labels':    json.dumps(chart_labels),
        'chart_lost':      json.dumps(chart_lost),
        'chart_found':     json.dumps(chart_found),
        'chart_resolved':  json.dumps(chart_resolved),
        'recent_resolved': recent_resolved,
        'view_mode':       view_mode,
        'start':           start.strftime('%Y-%m-%d'),
        'end':             end.strftime('%Y-%m-%d'),
    }
    return render(request, 'admin_dashboard/reports.html', context)
