from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Q
from datetime import timedelta
from .forms import (
    UserRegistrationForm, UserLoginForm, UserProfileForm,
    PremiumSubscriptionForm, PasswordResetRequestForm, PasswordResetSetForm
)
from .models import User, Subscription, Transaction
import random
import string


def register(request):
    """User registration view"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful! Welcome to FindMe.')
            return redirect('home')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'accounts/register.html', {'form': form})


def user_login(request):
    """User login view"""
    if request.user.is_authenticated:
        if request.user.is_staff or request.user.user_type == 'admin':
            return redirect('admin_dashboard:dashboard')
        return redirect('home')
    
    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            role = request.POST.get('role', 'user')
            
            user = authenticate(username=username, password=password)
            if user is not None:
                if role == 'admin':
                    if user.is_staff or user.user_type == 'admin':
                        login(request, user)
                        messages.success(request, f'Welcome to Admin Panel, {user.username}!')
                        return redirect('admin_dashboard:dashboard')
                    else:
                        messages.error(request, 'You do not have permission to log in as an admin.')
                        return redirect('accounts:login')
                else:
                    login(request, user)
                    messages.success(request, f'Welcome back, {user.username}!')
                    next_url = request.GET.get('next', 'home')
                    return redirect(next_url)
            else:
                messages.error(request, 'Invalid username or password. Please try again.')
    else:
        form = UserLoginForm()
    
    return render(request, 'accounts/login.html', {'form': form})


def user_logout(request):
    """User logout view"""
    logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('home')


# ──────────────────────────────────────────────
#  Password Reset Views (Forgot Password Flow)
# ──────────────────────────────────────────────

def password_reset_request(request):
    """Step 1: User enters email to receive a password reset link"""
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            user = form.user  # Set by form's clean_email()
            # Generate token and uid
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))

            # Build reset link
            reset_url = request.build_absolute_uri(
                f'/accounts/password-reset-confirm/{uid}/{token}/'
            )

            # Determine which email to send to
            target_email = form.cleaned_data['email']

            # Send email (console backend in dev)
            subject = 'FindMe - Password Reset Request'
            message = render_to_string('accounts/password_reset_email.html', {
                'user': user,
                'reset_url': reset_url,
            })
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [target_email])

            messages.success(
                request,
                'Password reset link has been sent to your email. '
                'Check your inbox (or console in development mode).'
            )
            return redirect('accounts:password_reset_done')
    else:
        form = PasswordResetRequestForm()

    return render(request, 'accounts/password_reset_request.html', {'form': form})


def password_reset_done(request):
    """Step 2: Confirmation page after sending the reset email"""
    return render(request, 'accounts/password_reset_done.html')


def password_reset_confirm(request, uidb64, token):
    """Step 3: User clicks the link and sets a new password"""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            form = PasswordResetSetForm(user, request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, 'Your password has been reset successfully! You can now login.')
                return redirect('accounts:password_reset_complete')
        else:
            form = PasswordResetSetForm(user)

        return render(request, 'accounts/password_reset_confirm.html', {
            'form': form,
            'validlink': True,
        })
    else:
        return render(request, 'accounts/password_reset_confirm.html', {
            'validlink': False,
        })


def password_reset_complete(request):
    """Step 4: Success page after password has been reset"""
    return render(request, 'accounts/password_reset_complete.html')


# ──────────────────────────────────────────────
#  Profile & Account Views
# ──────────────────────────────────────────────

@login_required
def profile(request):
    """User profile view"""
    request.user.check_and_reset_premium()
    transactions = Transaction.objects.filter(user=request.user)[:10]
    subscriptions = Subscription.objects.filter(user=request.user)[:5]
    
    # Calculate stats
    items_posted = request.user.items.count()
    items_found = request.user.items.filter(item_type='found').count()
    items_lost = request.user.items.filter(item_type='lost').count()
    
    context = {
        'transactions': transactions,
        'subscriptions': subscriptions,
        'items_posted': items_posted,
        'items_found': items_found,
        'items_lost': items_lost,
    }
    return render(request, 'accounts/profile.html', context)


@login_required
def edit_profile(request):
    """Edit user profile"""
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('accounts:profile')
    else:
        form = UserProfileForm(instance=request.user)
    
    return render(request, 'accounts/edit_profile.html', {'form': form})


@login_required
def upgrade_to_premium(request):
    """Upgrade to premium subscription (simulated payment)"""
    request.user.check_and_reset_premium()
    
    if request.user.is_premium:
        messages.info(request, 'You are already a premium user!')
        return redirect('accounts:profile')
    
    if request.method == 'POST':
        form = PremiumSubscriptionForm(request.POST)
        if form.is_valid():
            duration_days = int(form.cleaned_data['duration'])
            payment_method = form.cleaned_data['payment_method']
            amount = form.get_amount()
            
            # Simulate payment processing
            # In a real app, this would integrate with payment gateway
            
            # Update user to premium
            request.user.is_premium = True
            request.user.user_type = 'premium'
            request.user.premium_expiry = timezone.now() + timedelta(days=duration_days)
            request.user.save()
            
            # Create subscription record
            Subscription.objects.create(
                user=request.user,
                end_date=request.user.premium_expiry,
                status='active',
                payment_amount=amount,
                payment_method=payment_method
            )
            
            messages.success(request, f'Congratulations! You are now a premium user for {duration_days} days!')
            return redirect('accounts:profile')
    else:
        form = PremiumSubscriptionForm()
    
    return render(request, 'accounts/upgrade_premium.html', {'form': form})


@login_required
def points_history(request):
    """View points transaction history"""
    transactions = Transaction.objects.filter(user=request.user)
    
    context = {
        'transactions': transactions,
        'points_balance': request.user.points_balance,
    }
    return render(request, 'accounts/points_history.html', context)
