from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.models import Transaction
from .models import RedeemRequest
from .forms import RedeemRequestForm

# ─────────────────────────────────────────────
#  BUSINESS RULES
#  Change these values here if needed for viva.
# ─────────────────────────────────────────────
POINTS_PER_UNIT = 100   # 100 points = 1 unit
MONEY_PER_UNIT  = 50    # 1 unit     = Rs. 50
MIN_REDEEM_PTS  = 500   # minimum points required to submit a redeem request


def calc_amount(points):
    """
    Convert points to NPR amount.
    Formula: (points / 100) * 50
    Example: 500 points → Rs. 250
    """
    return (points / POINTS_PER_UNIT) * MONEY_PER_UNIT


def earn_points(user, points, reason):
    """
    Helper function: award points to a user and record the transaction.
    Call this from anywhere a user should earn points.

    Example:
        earn_points(request.user, 10, 'Posted a found item')
    """
    user.points_balance += points
    user.save(update_fields=['points_balance'])

    # Record in transaction history (shown on rewards page)
    Transaction.objects.create(
        user=user,
        transaction_type='earned',
        points=points,
        description=reason,
    )


# ─────────────────────────────────────────────
#  USER VIEWS
# ─────────────────────────────────────────────

@login_required
def rewards_dashboard(request):
    """
    Main rewards page — visible to ALL logged-in users.
    Shows: points balance, premium status, redeemable amount,
           points history, and redeem button (premium only).
    """
    user = request.user

    # Points transaction history (last 20 entries)
    history = Transaction.objects.filter(user=user).order_by('-created_at')[:20]

    # The user's redeem requests (last 10)
    redeem_requests = RedeemRequest.objects.filter(user=user).order_by('-requested_at')[:10]

    # How much money the current balance is worth
    redeemable_amount = calc_amount(user.points_balance)

    context = {
        'user': user,
        'history': history,
        'redeem_requests': redeem_requests,
        'redeemable_amount': redeemable_amount,
        'min_redeem_pts': MIN_REDEEM_PTS,
        'min_redeem_amount': calc_amount(MIN_REDEEM_PTS),
    }
    return render(request, 'rewards/rewards_dashboard.html', context)


@login_required
def submit_redeem(request):
    """
    POST: Submit a new redeem request.
    - Only premium users are allowed.
    - User must have at least MIN_REDEEM_PTS points.
    - User provides their Khalti number for admin to send payment.
    - Points are NOT deducted here — deducted only when admin approves.
    """
    user = request.user

    # Block: non-premium users cannot redeem
    if not user.is_premium:
        messages.error(
            request,
            'Only premium users can redeem reward points. '
            'Upgrade to premium to unlock this feature.'
        )
        return redirect('rewards:rewards_dashboard')

    # Block: not enough points
    if user.points_balance < MIN_REDEEM_PTS:
        messages.error(
            request,
            f'You need at least {MIN_REDEEM_PTS} points to redeem. '
            f'You currently have {user.points_balance} points.'
        )
        return redirect('rewards:rewards_dashboard')

    if request.method == 'POST':
        form = RedeemRequestForm(request.POST)

        if form.is_valid():
            points = form.cleaned_data['points_requested']
            payout_reference = form.cleaned_data.get('payout_reference', '')

            # Double-check points are still sufficient (safety check)
            if points > user.points_balance:
                messages.error(request, 'You do not have enough points for this request.')
                return render(request, 'rewards/submit_redeem.html', {
                    'form': form,
                    'user': user,
                    'min_redeem_pts': MIN_REDEEM_PTS,
                    'redeemable_amount': calc_amount(user.points_balance),
                })

            # Calculate NPR amount using fixed formula
            amount = calc_amount(points)

            # Save the request — status is 'pending' by default
            # Points are NOT deducted yet (deducted when admin approves)
            RedeemRequest.objects.create(
                user=user,
                points_requested=points,
                amount=amount,
                payout_reference=payout_reference,
                status='pending',
            )

            messages.success(
                request,
                f'Redeem request for {points} points (Rs. {amount:.0f}) submitted successfully! '
                'Please wait for admin to review your request.'
            )
            return redirect('rewards:my_redeem_requests')

    else:
        # GET: show an empty form
        form = RedeemRequestForm()

    context = {
        'form': form,
        'user': user,
        'min_redeem_pts': MIN_REDEEM_PTS,
        'min_redeem_amount': calc_amount(MIN_REDEEM_PTS),
        'redeemable_amount': calc_amount(user.points_balance),
    }
    return render(request, 'rewards/submit_redeem.html', context)


@login_required
def my_redeem_requests(request):
    """
    Shows the logged-in user's full redeem request history.
    """
    redeem_requests = RedeemRequest.objects.filter(
        user=request.user
    ).order_by('-requested_at')

    context = {
        'redeem_requests': redeem_requests,
    }
    return render(request, 'rewards/my_redeem_requests.html', context)
