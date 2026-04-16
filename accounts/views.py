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
from .models import User, Subscription, Transaction, KhaltiPayment
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
    """Upgrade to premium subscription via Khalti ePay v2."""
    request.user.check_and_reset_premium()

    if request.user.is_premium:
        messages.info(request, 'You are already a premium user!')
        return redirect('accounts:profile')

    return render(request, 'accounts/upgrade_premium.html', {
        'khalti_debug': settings.DEBUG,
    })



@login_required
def points_history(request):
    """View points transaction history"""
    transactions = Transaction.objects.filter(user=request.user)
    
    context = {
        'transactions': transactions,
        'points_balance': request.user.points_balance,
    }
    return render(request, 'accounts/points_history.html', context)


# ──────────────────────────────────────────────────────────────
#  Khalti Payment Views  (Checkout Widget + Token Verification)
# ──────────────────────────────────────────────────────────────
#
#  FLOW (for viva):
#  1. Frontend loads Khalti JS widget (CDN)
#  2. User clicks button → Khalti popup opens
#  3. User pays → Khalti calls onSuccess(payload) with token + amount
#  4. JS fetch() sends token + amount to /accounts/khalti-verify/
#  5. Django verifies token with Khalti API using SECRET KEY
#     (In DEBUG mode, verification is simulated to handle sandbox issues)
#  6. On success: save KhaltiPayment, mark user is_premium=True
#
# ──────────────────────────────────────────────────────────────

import requests as http_requests
import json
import uuid
from django.http import JsonResponse
from django.urls import reverse

KHALTI_SECRET_KEY   = getattr(settings, 'KHALTI_SECRET_KEY', 'e5639a56c40a45c2a3f1f176e3b9b859')
KHALTI_PUBLIC_KEY   = getattr(settings, 'KHALTI_PUBLIC_KEY',  'b5b0db5b0f704aae922bf351f782c275')
KHALTI_API_URL      = getattr(settings, 'KHALTI_API_URL', 'https://a.khalti.com/api/v2/')
KHALTI_VERIFY_URL   = f'{KHALTI_API_URL}payment/verify/'
KHALTI_INITIATE_URL = getattr(settings, 'KHALTI_INITIATE_URL', 'https://a.khalti.com/api/v2/epayment/initiate/')
KHALTI_LOOKUP_URL   = getattr(settings, 'KHALTI_LOOKUP_URL', 'https://a.khalti.com/api/v2/epayment/lookup/')


def _mark_user_premium(user, token, amount):
    """Helper: save payment record and upgrade user to premium (30 days)."""
    KhaltiPayment.objects.create(
        user=user,
        token=token,
        amount=amount,
        status='success'
    )
    user.is_premium = True
    user.user_type  = 'premium'
    user.premium_expiry = timezone.now() + timedelta(days=30)
    user.save()
    Subscription.objects.create(
        user=user,
        end_date=user.premium_expiry,
        status='active',
        payment_amount=int(amount) / 100,   # paisa → NPR
        payment_method='Khalti'
    )


@login_required
def khalti_verify(request):
    """
    Receives token + amount from the Khalti v1 widget's onSuccess callback.

    Steps:
      1. JS widget calls onSuccess(payload) with payload.token and payload.amount
      2. Frontend sends { token, amount } as JSON to this endpoint via fetch()
      3. This view verifies the token with Khalti's API (or auto-approves in DEBUG)
      4. On success: mark user as Premium and return { success: true }

    Sandbox / DEBUG mode:
      Khalti sandbox tokens are unreliable to verify externally, so in DEBUG=True
      we skip the API call and approve automatically — safe for demo/viva.

    Production mode:
      Calls https://khalti.com/api/v2/payment/verify/ with the secret key.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'POST required.'}, status=405)

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON body.'}, status=400)

    token  = body.get('token', '')
    amount = body.get('amount', 50000)   # default 50000 paisa = NPR 500

    if not token:
        return JsonResponse({'success': False, 'message': 'token is required.'}, status=400)

    # ── DEBUG / SANDBOX mode: skip external API call ──────────────────────
    if settings.DEBUG:
        print(f'\n[KHALTI VERIFY] DEBUG mode — token={token}  amount={amount} → auto-success\n')
        _mark_user_premium(request.user, token, amount)
        return JsonResponse({
            'success': True,
            'message': 'Payment verified! You are now a Premium user.'
        })

    # ── PRODUCTION: verify token with Khalti API ─────────────────────────
    headers = {'Authorization': f'Key {KHALTI_SECRET_KEY}'}
    try:
        resp = http_requests.post(
            KHALTI_VERIFY_URL,
            data={'token': token, 'amount': amount},
            headers=headers,
            timeout=15
        )
    except Exception as exc:
        return JsonResponse({'success': False, 'message': f'Network error: {exc}'}, status=500)

    print(f'\n[KHALTI VERIFY] status={resp.status_code}  body={resp.text[:300]}\n')

    if resp.status_code == 200:
        _mark_user_premium(request.user, token, amount)
        return JsonResponse({'success': True, 'message': 'Payment verified! You are now a Premium user.'})

    # verification failed
    try:
        detail = resp.json()
    except Exception:
        detail = resp.text[:200]
    return JsonResponse(
        {'success': False, 'message': 'Payment verification failed.', 'detail': detail},
        status=400
    )



@login_required
def khalti_initiate(request):
    """
    ePay v2 — Step 1: Initiate payment server-side.
    Calls Khalti's initiate API and redirects the user to Khalti's
    hosted checkout page (phone → MPIN → OTP — no bank selection).
    """
    if request.user.is_premium:
        messages.info(request, 'You are already a premium user!')
        return redirect('accounts:profile')

    return_url  = request.build_absolute_uri(reverse('accounts:khalti_callback'))
    website_url = request.build_absolute_uri('/')

    order_id = f'premium-{request.user.id}-{uuid.uuid4().hex[:8]}'

    # Khalti ePay v2 requires these exact field names
    payload = {
        "return_url":        return_url,
        "website_url":       website_url,
        "amount":            50000,                    # 50,000 paisa = NPR 500
        "purchase_order_id": order_id,
        "purchase_order_name": "FindMe Premium - 1 Month",
        "customer_name":     request.user.get_full_name() or request.user.username,
        "customer_email":    request.user.email or 'test@example.com',
        "customer_phone":    request.user.phone_number or '9800000001',
    }

    headers = {
        "Authorization": f"Key {KHALTI_SECRET_KEY}",
        "Content-Type":  "application/json",
    }

    print(f'\n[KHALTI INITIATE] Sending payload: {payload}\n')
    print(f'[KHALTI INITIATE] URL: {KHALTI_INITIATE_URL}\n')
    print(f'[KHALTI INITIATE] Secret Key (first 20 chars): {KHALTI_SECRET_KEY[:20]}...\n')

    try:
        resp = http_requests.post(
            KHALTI_INITIATE_URL,
            json=payload,
            headers=headers,
            timeout=15
        )
        data = resp.json()
        print(f'\n[KHALTI INITIATE] status={resp.status_code}  body={str(data)}\n')

        if resp.status_code == 200 and 'payment_url' in data:
            # Save pidx in session so we can verify on callback
            request.session['khalti_pidx']     = data.get('pidx', '')
            request.session['khalti_order_id'] = order_id
            
            payment_url = data['payment_url']
            # Fix Khalti sandbox bug where it returns production URL for test keys
            if 'a.khalti.com' in KHALTI_INITIATE_URL or 'dev.khalti.com' in KHALTI_INITIATE_URL:
                payment_url = payment_url.replace('https://pay.khalti.com/', 'https://test-pay.khalti.com/')

            print(f'[KHALTI INITIATE] Success! Redirecting to: {payment_url}\n')
            return redirect(payment_url)
        else:
            error_detail = data.get('detail', data.get('error_key', str(data)))
            print(f'[KHALTI INITIATE] ERROR: {error_detail}\n')
            messages.error(request, f'Khalti error: {error_detail}')
            return redirect('accounts:upgrade_premium')

    except Exception as exc:
        print(f'[KHALTI INITIATE] Exception: {exc}\n')
        messages.error(request, f'Network error contacting Khalti: {exc}')
        return redirect('accounts:upgrade_premium')


@login_required
def khalti_callback(request):
    """
    ePay v2 — Step 2: Khalti redirects back here after the user pays.
    We then verify the payment with the Lookup API before upgrading.
    """
    status = request.GET.get('status', '')
    pidx   = request.GET.get('pidx', '')

    print(f'\n[KHALTI CALLBACK] status={status}  pidx={pidx}\n')

    if status == 'User canceled':
        messages.warning(request, 'Payment was cancelled. You can try again.')
        return redirect('accounts:upgrade_premium')

    if not pidx:
        messages.error(request, 'Invalid payment callback — missing pidx.')
        return redirect('accounts:upgrade_premium')

    if request.user.is_premium:
        # Already upgraded (duplicate callback)
        return redirect('accounts:khalti_success')

    # ── Lookup / verify ─────────────────────────────────────────────
    headers = {
        "Authorization": f"Key {KHALTI_SECRET_KEY}",
        "Content-Type":  "application/json",
    }
    try:
        resp = http_requests.post(
            KHALTI_LOOKUP_URL,
            json={"pidx": pidx},
            headers=headers,
            timeout=15
        )
        data = resp.json()
        print(f'\n[KHALTI LOOKUP] status={resp.status_code}  body={str(data)[:300]}\n')

        if resp.status_code == 200 and data.get('status') == 'Completed':
            amount = data.get('total_amount', 50000)
            _mark_user_premium(request.user, pidx, amount)
            messages.success(request, 'Payment verified! You are now a Premium user. 🎉')
            return redirect('accounts:khalti_success')
        else:
            payment_status = data.get('status', 'Unknown')
            messages.error(request, f'Payment not completed. Khalti status: {payment_status}')
            return redirect('accounts:upgrade_premium')

    except Exception as exc:
        messages.error(request, f'Verification error: {exc}')
        return redirect('accounts:upgrade_premium')


@login_required
def khalti_simulate(request):
    """
    Demo-only endpoint: instantly simulates a successful Khalti payment.
    Only active when DEBUG=True.
    """
    if not settings.DEBUG:
        return JsonResponse({'success': False, 'message': 'Not available in production.'}, status=403)

    if request.user.is_premium:
        messages.info(request, 'You are already a premium user!')
        return redirect('accounts:profile')

    fake_pidx = f'demo-{uuid.uuid4().hex[:16]}'
    _mark_user_premium(request.user, fake_pidx, 50000)
    print(f'\n[KHALTI SIMULATE] User {request.user.username} upgraded to premium (demo pidx: {fake_pidx})\n')
    messages.success(request, 'Demo payment successful! You are now a Premium user.')
    return redirect('accounts:khalti_success')


@login_required
def khalti_success(request):
    """Simple success landing page after Khalti payment"""
    return render(request, 'accounts/khalti_success.html')


@login_required
def cancel_subscription(request):
    """Cancel the user's active premium subscription."""
    if request.method != 'POST':
        return redirect('accounts:profile')

    if not request.user.is_premium:
        messages.error(request, 'You do not have an active subscription to cancel.')
        return redirect('accounts:profile')

    # Mark all active subscriptions as cancelled
    Subscription.objects.filter(user=request.user, status='active').update(status='cancelled')

    # Revoke premium status immediately
    request.user.is_premium = False
    request.user.user_type = 'normal'
    request.user.premium_expiry = None
    request.user.save(update_fields=['is_premium', 'user_type', 'premium_expiry'])

    messages.success(request, 'Your premium subscription has been cancelled. You have been moved back to a normal account.')
    return redirect('accounts:profile')
