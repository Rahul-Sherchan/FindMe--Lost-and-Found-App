from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import GiftCard, Redemption
from accounts.models import Transaction
import random
import string


@login_required
def giftcard_catalog(request):
    """View available gift cards for redemption"""
    giftcards = GiftCard.objects.filter(is_active=True).order_by('points_required')
    
    context = {
        'giftcards': giftcards,
        'user_points': request.user.points_balance,
    }
    return render(request, 'rewards/giftcard_catalog.html', context)


@login_required
def redeem_giftcard(request, pk):
    """Redeem points for a gift card"""
    giftcard = get_object_or_404(GiftCard, pk=pk, is_active=True)
    
    # Check if gift card is available
    if not giftcard.is_available:
        messages.error(request, 'This gift card is currently unavailable.')
        return redirect('rewards:giftcard_catalog')
    
    # Check if user has enough points
    if request.user.points_balance < giftcard.points_required:
        messages.error(request, f'You need {giftcard.points_required - request.user.points_balance} more points to redeem this gift card.')
        return redirect('rewards:giftcard_catalog')
    
    if request.method == 'POST':
        # Deduct points from user
        request.user.points_balance -= giftcard.points_required
        request.user.save()
        
        # Create transaction record
        Transaction.objects.create(
            user=request.user,
            transaction_type='redeemed',
            points=giftcard.points_required,
            description=f'Redeemed {giftcard.name}'
        )
        
        # Generate random code (simulated)
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
        
        # Create redemption record
        redemption = Redemption.objects.create(
            user=request.user,
            giftcard=giftcard,
            points_spent=giftcard.points_required,
            status='completed',
            code=code
        )
        redemption.completed_at = redemption.created_at
        redemption.save()
        
        # Update stock if not unlimited
        if giftcard.stock > 0:
            giftcard.stock -= 1
            giftcard.save()
        
        messages.success(request, f'Gift card redeemed successfully! Your code: {code}')
        return redirect('rewards:redemption_history')
    
    context = {
        'giftcard': giftcard,
    }
    return render(request, 'rewards/redeem_confirm.html', context)


@login_required
def redemption_history(request):
    """View redemption history"""
    redemptions = Redemption.objects.filter(user=request.user).order_by('-created_at')
    
    context = {
        'redemptions': redemptions,
    }
    return render(request, 'rewards/redemption_history.html', context)
