from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, SetPasswordForm
from django.core.exceptions import ValidationError
from django.db import models
from .models import User, Subscription
from datetime import datetime, timedelta
import re


class UserRegistrationForm(UserCreationForm):
    """User registration form"""
    email = forms.EmailField(required=True)
    recovery_email = forms.EmailField(
        required=False,
        help_text="Optional recovery email for password resets",
        widget=forms.EmailInput(attrs={'placeholder': 'Recovery email (optional)'})
    )
    phone_number = forms.CharField(max_length=20, required=False)
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'recovery_email', 'password1', 'password2', 'phone_number', 'address']
    
    def clean_recovery_email(self):
        """Validate that recovery email is different from primary email"""
        recovery = self.cleaned_data.get('recovery_email')
        primary = self.cleaned_data.get('email')
        if recovery and primary and recovery.lower() == primary.lower():
            raise ValidationError("Recovery email must be different from your primary email.")
        return recovery

    def clean_phone_number(self):
        """Clean and validate phone number"""
        phone = self.cleaned_data.get('phone_number', '')
        if phone:
            # Remove spaces, dashes, and parentheses
            cleaned = re.sub(r'[\s\-\(\)]', '', phone)
            # Ensure it starts with + and contains reasonable digits
            if not re.match(r'^\+?[0-9]{7,20}$', cleaned):
                raise ValidationError("Enter a valid phone number with country code.")
            return cleaned
        return phone

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.recovery_email = self.cleaned_data.get('recovery_email') or None
        user.user_type = 'normal'
        user.is_premium = False
        if commit:
            user.save()
        return user


class UserLoginForm(AuthenticationForm):
    """User login form"""
    username = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Username'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Password'}))


class UserProfileForm(forms.ModelForm):
    """User profile edit form"""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'recovery_email', 'phone_number', 'address', 'profile_picture']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_recovery_email(self):
        """Validate that recovery email is different from primary email"""
        recovery = self.cleaned_data.get('recovery_email')
        primary = self.cleaned_data.get('email')
        if recovery and primary and recovery.lower() == primary.lower():
            raise ValidationError("Recovery email must be different from your primary email.")
        return recovery


class PasswordResetRequestForm(forms.Form):
    """Form for requesting a password reset — supports both primary and recovery email"""
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'placeholder': 'Enter your primary or recovery email',
            'class': 'form-control',
        }),
        help_text="Enter the email address associated with your account."
    )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        # Check if any user has this as primary or recovery email
        user = User.objects.filter(
            models.Q(email__iexact=email) | models.Q(recovery_email__iexact=email)
        ).first()
        if not user:
            raise ValidationError("No account found with this email address.")
        self.user = user
        return email


class PasswordResetSetForm(SetPasswordForm):
    """Form for setting a new password during reset"""
    pass


class PremiumSubscriptionForm(forms.Form):
    """Form for premium subscription (simulated payment)"""
    DURATION_CHOICES = (
        (30, '1 Month - NPR 500'),
        (90, '3 Months - NPR 1200'),
        (365, '1 Year - NPR 4000'),
    )
    
    duration = forms.ChoiceField(choices=DURATION_CHOICES, widget=forms.RadioSelect)
    payment_method = forms.ChoiceField(
        choices=[
            ('esewa', 'eSewa'),
            ('khalti', 'Khalti'),
            ('bank', 'Bank Transfer'),
        ],
        widget=forms.RadioSelect
    )
    
    def get_amount(self):
        """Get payment amount based on duration"""
        duration = int(self.cleaned_data.get('duration', 30))
        amounts = {30: 500, 90: 1200, 365: 4000}
        return amounts.get(duration, 500)
