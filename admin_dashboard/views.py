from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.db import transaction as db_transaction
from django.http import JsonResponse
import json
from datetime import date, datetime, timedelta
from django.db.models import Count, Q
from django.db.models.functions import TruncMonth, TruncWeek
from accounts.models import User, Transaction
from items.models import Item, Claim
from notifications.models import Notification, SystemNotification
from rewards.models import RedeemRequest
from messaging.models import Message
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from .forms import AdminProfileForm

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
    total_claims = Claim.objects.count()
    approved_claims = Claim.objects.filter(status='approved').count()
    rejected_claims = Claim.objects.filter(status='rejected').count()
    
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
        'total_claims': total_claims,
        'approved_claims': approved_claims,
        'rejected_claims': rejected_claims,
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
def calendar_analytics(request):
    """Display calendar analytics view with empty calendar script"""
    try:
        year_param = request.GET.get('year')
        month_param = request.GET.get('month')
        
        # Use current date as default
        today = timezone.now()
        year = today.year
        month = today.month
        
        # Override with parameters if provided
        if year_param:
            try:
                year = int(year_param)
                # Validate year range
                if year < 1900 or year > 2100:
                    year = today.year
            except (ValueError, TypeError):
                year = today.year
        
        if month_param:
            try:
                month = int(month_param)
                # Validate month range
                if month < 1 or month > 12:
                    month = today.month
            except (ValueError, TypeError):
                month = today.month
        
        context = {
            'year': year,
            'month': month,
            'pending_claims_count': get_pending_claims_count(),
            'current_date': timezone.now().date(),
        }
        return render(request, 'admin_dashboard/calendar_analytics.html', context)
    except Exception as e:
        import traceback
        traceback.print_exc()
        # Return a safe response even if something goes wrong
        context = {
            'year': 2026,
            'month': 4,
            'pending_claims_count': 0,
            'current_date': timezone.now().date(),
            'error': 'An error occurred loading the calendar'
        }
        return render(request, 'admin_dashboard/calendar_analytics.html', context)


@login_required
@user_passes_test(is_admin)
def calendar_data_api(request):
    """API endpoint to fetch analytics data for a specific date or date range"""
    date_str = request.GET.get('date', None)
    
    if not date_str:
        return JsonResponse({'error': 'Date parameter required'}, status=400)
    
    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=400)
    
    try:
        # Fetch data for the given date
        # 1. New users registered on this date
        new_users = User.objects.filter(
            date_joined__date=target_date
        ).count()
        
        # 2. Posts created on this date (separated by type)
        lost_posts = Item.objects.filter(
            created_at__date=target_date,
            item_type='lost'
        ).count()
        
        found_posts = Item.objects.filter(
            created_at__date=target_date,
            item_type='found'
        ).count()
        
        total_posts = lost_posts + found_posts
        
        # 3. Recovered items (items marked as resolved/claimed on this date)
        recovered_items = Item.objects.filter(
            Q(status='resolved') | Q(status='claimed'),
            updated_at__date=target_date
        ).count()
        
        # 4. Messages exchanged on this date
        messages_count = Message.objects.filter(
            created_at__date=target_date
        ).count()
        
        # Calculate activity level (0-100) for color-coding
        # Weights: Users (2), Posts (3), Recovered (5), Messages (1)
        activity_score = (
            (int(new_users) * 2) +          # Up to 20 points
            (int(total_posts) * 3) +        # Up to 40+ points
            (int(recovered_items) * 5) +    # Up to 20+ points
            (int(messages_count) * 1)       # Up to 20+ points
        )
        
        # Normalize to 0-100 scale and cap at 100
        activity_level = min(int((activity_score / 100) * 100), 100)
        activity_level = max(0, activity_level)  # Ensure not negative
        
        # Determine activity category
        if activity_level >= 60:
            activity_category = 'high'  # Green
        elif activity_level >= 30:
            activity_category = 'medium'  # Yellow
        else:
            activity_category = 'low'  # Red
        
        return JsonResponse({
            'date': date_str,
            'new_users': int(new_users),
            'lost_posts': int(lost_posts),
            'found_posts': int(found_posts),
            'total_posts': int(total_posts),
            'recovered_items': int(recovered_items),
            'messages_count': int(messages_count),
            'activity_level': int(activity_level),
            'activity_category': activity_category,
        }, safe=True)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)


@login_required
@user_passes_test(is_admin)
def calendar_month_data_api(request):
    """API endpoint to fetch activity data for all dates in a month for color-coding"""
    year = request.GET.get('year')
    month = request.GET.get('month')
    
    if not year or not month:
        return JsonResponse({'error': 'Year and month parameters required'}, status=400)
    
    try:
        year = int(year)
        month = int(month)
        
        # Validate year and month
        if year < 1900 or year > 2100:
            return JsonResponse({'error': 'Year must be between 1900 and 2100'}, status=400)
        if month < 1 or month > 12:
            return JsonResponse({'error': 'Month must be between 1 and 12'}, status=400)
            
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid year or month. Must be integers.'}, status=400)
    
    try:
        # Generate list of all dates in the month
        from calendar import monthrange
        last_day = monthrange(year, month)[1]
        
        activity_data = {}
        
        for day in range(1, last_day + 1):
            try:
                date_obj = date(year, month, day)
                
                # Calculate activity score for this day
                new_users = User.objects.filter(date_joined__date=date_obj).count()
                lost_posts = Item.objects.filter(created_at__date=date_obj, item_type='lost').count()
                found_posts = Item.objects.filter(created_at__date=date_obj, item_type='found').count()
                recovered = Item.objects.filter(
                    Q(status='resolved') | Q(status='claimed'),
                    updated_at__date=date_obj
                ).count()
                msg_count = Message.objects.filter(created_at__date=date_obj).count()
                
                # Ensure all values are integers
                new_users = int(new_users) if new_users else 0
                lost_posts = int(lost_posts) if lost_posts else 0
                found_posts = int(found_posts) if found_posts else 0
                recovered = int(recovered) if recovered else 0
                msg_count = int(msg_count) if msg_count else 0
                
                activity_score = (new_users * 2) + ((lost_posts + found_posts) * 3) + (recovered * 5) + (msg_count * 1)
                activity_level = min(int((activity_score / 100) * 100), 100)
                activity_level = max(0, activity_level)  # Ensure not negative
                
                if activity_level >= 60:
                    category = 'high'
                elif activity_level >= 30:
                    category = 'medium'
                else:
                    category = 'low'
                
                activity_data[day] = {
                    'level': activity_level,
                    'category': category,
                }
            except Exception as e:
                # Log error for this specific day but continue with others
                print(f"Error calculating activity for {year}-{month}-{day}: {str(e)}")
                activity_data[day] = {
                    'level': 0,
                    'category': 'low',
                }
        
        return JsonResponse({
            'year': year,
            'month': month,
            'data': activity_data,
        }, safe=True)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)


@login_required
@user_passes_test(is_admin)
def manage_announcements(request):
    """View and create global system announcements"""
    if request.method == 'POST':
        title = request.POST.get('title')
        message = request.POST.get('message')
        
        if title and message:
            SystemNotification.objects.create(
                title=title,
                message=message,
                created_by=request.user
            )
            messages.success(request, 'Announcement created globally for all users.')
            return redirect('admin_dashboard:manage_announcements')
        else:
            messages.error(request, 'Title and message are required.')
            
    announcements = SystemNotification.objects.all().order_by('-created_at')
    
    context = {
        'announcements': announcements,
        'pending_claims_count': get_pending_claims_count(),
    }
    return render(request, 'admin_dashboard/manage_announcements.html', context)

@login_required
@user_passes_test(is_admin)
def delete_announcement(request, pk):
    """Delete a global system announcement"""
    announcement = get_object_or_404(SystemNotification, pk=pk)
    
    if request.method == 'POST':
        announcement.delete()
        messages.success(request, 'Announcement deleted successfully.')
        
    return redirect('admin_dashboard:manage_announcements')


@login_required
@user_passes_test(is_admin)
def admin_profile(request):
    """Allows admin to view/edit their profile and change their password securely."""
    # Initialize both forms
    profile_form = AdminProfileForm(instance=request.user)
    password_form = PasswordChangeForm(request.user)

    if request.method == 'POST':
        if 'update_profile' in request.POST:
            profile_form = AdminProfileForm(request.POST, request.FILES, instance=request.user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, 'Profile updated successfully.')
                return redirect('admin_dashboard:admin_profile')
            else:
                messages.error(request, 'Please correct the errors in the profile form.')
        
        elif 'change_password' in request.POST:
            password_form = PasswordChangeForm(request.user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)  # Keep user logged in
                messages.success(request, 'Your password was successfully updated!')
                return redirect('admin_dashboard:admin_profile')
            else:
                messages.error(request, 'Please correct the errors in the password form.')

    context = {
        'profile_form': profile_form,
        'password_form': password_form,
        'pending_claims_count': get_pending_claims_count(),
    }
    return render(request, 'admin_dashboard/admin_profile.html', context)


# ─────────────────────────────────────────────
#  REDEEM REQUEST MANAGEMENT
# ─────────────────────────────────────────────

def get_pending_redeem_count():
    """Utility: count of pending redeem requests (used in sidebar badge)"""
    return RedeemRequest.objects.filter(status='pending').count()


@login_required
@user_passes_test(is_admin)
def manage_redeem_requests(request):
    """
    Admin view: list all redeem requests.
    Filter by status using ?status=pending / approved / rejected / paid.
    """
    # Get filter from query string
    fstatus = request.GET.get('status', '')

    redeem_requests = RedeemRequest.objects.select_related('user').order_by('-requested_at')

    # Apply status filter if valid
    if fstatus in ['pending', 'approved', 'rejected', 'paid']:
        redeem_requests = redeem_requests.filter(status=fstatus)

    context = {
        'redeem_requests': redeem_requests,
        'current_filter': fstatus,
        'pending_claims_count': get_pending_claims_count(),
        'pending_redeem_count': get_pending_redeem_count(),
    }
    return render(request, 'admin_dashboard/manage_redeem_requests.html', context)


@login_required
@user_passes_test(is_admin)
def approve_redeem_request(request, pk):
    """
    Admin: Approve a redeem request.
    - Deducts points from user's balance.
    - Creates a Transaction record (type = redeemed).
    - Sets status to 'approved' and records reviewed_at.
    """
    redeem_req = get_object_or_404(RedeemRequest, pk=pk)

    # Only pending requests can be approved
    if redeem_req.status != 'pending':
        messages.warning(request, f'This request is already {redeem_req.get_status_display()}.')
        return redirect('admin_dashboard:manage_redeem_requests')

    if request.method == 'POST':
        user = redeem_req.user
        admin_note = request.POST.get('admin_note', '').strip()

        # Safety check: make sure user still has enough points
        if user.points_balance < redeem_req.points_requested:
            messages.error(
                request,
                f'{user.username} no longer has enough points. '
                f'They have {user.points_balance} pts, request is for {redeem_req.points_requested} pts.'
            )
            return redirect('admin_dashboard:manage_redeem_requests')

        # Deduct points from user
        user.points_balance -= redeem_req.points_requested
        user.save(update_fields=['points_balance'])

        # Record the deduction in transaction history
        Transaction.objects.create(
            user=user,
            transaction_type='redeemed',
            points=redeem_req.points_requested,
            description=f'Redeemed {redeem_req.points_requested} points for Rs. {redeem_req.amount:.0f}'
        )

        # Update the request
        redeem_req.status = 'approved'
        redeem_req.reviewed_at = timezone.now()
        redeem_req.admin_note = admin_note
        redeem_req.save()

        messages.success(
            request,
            f'Redeem request approved for {user.username}. '
            f'{redeem_req.points_requested} points deducted. Amount: Rs. {redeem_req.amount:.0f}'
        )
        return redirect('admin_dashboard:manage_redeem_requests')

    context = {
        'redeem_req': redeem_req,
        'pending_claims_count': get_pending_claims_count(),
        'pending_redeem_count': get_pending_redeem_count(),
    }
    return render(request, 'admin_dashboard/approve_redeem_request.html', context)


@login_required
@user_passes_test(is_admin)
def reject_redeem_request(request, pk):
    """
    Admin: Reject a redeem request.
    - No points are deducted.
    - Sets status to 'rejected'.
    """
    redeem_req = get_object_or_404(RedeemRequest, pk=pk)

    if redeem_req.status != 'pending':
        messages.warning(request, f'This request is already {redeem_req.get_status_display()}.')
        return redirect('admin_dashboard:manage_redeem_requests')

    if request.method == 'POST':
        admin_note = request.POST.get('admin_note', '').strip()

        redeem_req.status = 'rejected'
        redeem_req.reviewed_at = timezone.now()
        redeem_req.admin_note = admin_note
        redeem_req.save()

        messages.success(request, f'Redeem request rejected for {redeem_req.user.username}.')
        return redirect('admin_dashboard:manage_redeem_requests')

    context = {
        'redeem_req': redeem_req,
        'pending_claims_count': get_pending_claims_count(),
        'pending_redeem_count': get_pending_redeem_count(),
    }
    return render(request, 'admin_dashboard/reject_redeem_request.html', context)

@login_required
@user_passes_test(is_admin)
def mark_redeem_paid(request, pk):
    """
    Admin: Mark an approved redeem request as 'paid'.
    Use this after manually sending money to the user (via Khalti or other method).
    - Only 'approved' requests can be marked as paid.
    - Sets paid_at to record exactly when payment was confirmed.
    """
    redeem_req = get_object_or_404(RedeemRequest, pk=pk)

    if redeem_req.status != 'approved':
        messages.warning(request, 'Only approved requests can be marked as paid.')
        return redirect('admin_dashboard:manage_redeem_requests')

    if request.method == 'POST':
        admin_note = request.POST.get('admin_note', redeem_req.admin_note)
        now = timezone.now()

        redeem_req.status = 'paid'
        redeem_req.paid_at = now          # exact time payment was confirmed
        redeem_req.reviewed_at = redeem_req.reviewed_at or now
        redeem_req.admin_note = admin_note
        redeem_req.save()

        messages.success(
            request,
            f'Payment confirmed! Rs. {redeem_req.amount:.0f} marked as PAID for {redeem_req.user.username}.'
        )
        return redirect('admin_dashboard:manage_redeem_requests')

    # GET → just redirect back
    return redirect('admin_dashboard:manage_redeem_requests')
